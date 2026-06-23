#!/usr/bin/env python3
"""
compare_planners.py

Compares PDDL4J HSP against your PRW planner on:
blocksworld, depot, gripper, logistics.

Outputs:
  results.csv
  8 PNG figures: runtime + makespan for each domain
  comparison_report.pdf

Example:
  python compare_planners.py ^
    --pddl4j-jar "FULL_CLASSPATH_HERE" ^
    --prw-classes "C:\\path\\to\\build\\classes\\java\\main" ^
    --benchmarks "C:\\path\\to\\src\\test\\resources\\benchmarks\\pddl" ^
    --timeout 10 ^
    --max-problems 1 ^
    --debug
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


HSP_MAIN_CLASS = "fr.uga.pddl4j.planners.statespace.HSP"
PRW_MAIN_CLASS = "fr.uga.pddl4j.examples.prw.PRW"

DOMAIN_KEYWORDS = {
    "blocksworld": ["blocksworld", "blocks"],
    "depot": ["depot", "depots"],
    "gripper": ["gripper"],
    "logistics": ["logistics"],
}

ALL_DOMAINS = list(DOMAIN_KEYWORDS.keys())

PLAN_LINE_RE = re.compile(
    r"^\s*(?:\d+\s*[:.]?\s*)?\(\s*(?P<action>[^()]+?)\s*\)\s*(?:\[[^\]]*\])?\s*$"
)


def find_domain_file(dirpath, filenames):
    for filename in filenames:
        if filename.lower().endswith(".pddl") and "domain" in filename.lower():
            return os.path.join(dirpath, filename)
    return None


def discover_problems(benchmarks_root, domain_name, max_problems=None, debug=False):
    keywords = DOMAIN_KEYWORDS[domain_name]
    pairs = []

    for dirpath, _dirnames, filenames in os.walk(benchmarks_root):
        lower_path = dirpath.lower()

        if not any(keyword in lower_path for keyword in keywords):
            continue

        pddl_files = [f for f in filenames if f.lower().endswith(".pddl")]

        if not pddl_files:
            continue

        domain_file = find_domain_file(dirpath, pddl_files)

        if domain_file is None:
            if debug:
                print(f"[discover] skip {dirpath}: no domain*.pddl found")
            continue

        problem_files = [
            os.path.join(dirpath, f)
            for f in pddl_files
            if os.path.join(dirpath, f) != domain_file
        ]

        for problem_file in sorted(problem_files):
            pairs.append((domain_file, problem_file))

    pairs.sort(key=lambda item: item[1])

    if max_problems is not None:
        pairs = pairs[:max_problems]

    if debug:
        print(f"[discover] {domain_name}: found {len(pairs)} problem(s)")
        for domain_file, problem_file in pairs:
            print(f"    domain={domain_file}")
            print(f"    problem={problem_file}")

    return pairs


def build_hsp_command(jar, domain_file, problem_file, heuristic, timeout):
    return [
        "java",
        "-cp",
        jar,
        HSP_MAIN_CLASS,
        "-t",
        str(timeout),
        "-e",
        heuristic,
        domain_file,
        problem_file,
    ]


def build_prw_command(
    prw_classes,
    jar,
    domain_file,
    problem_file,
    timeout,
    heuristic="FAST_FORWARD",
    walks=30,
    depth=10,
    stagnation=1,
    seed=None,
):
    classpath = prw_classes + os.pathsep + jar

    cmd = [
        "java",
        "-cp",
        classpath,
        PRW_MAIN_CLASS,
        "-t",
        str(timeout),
        "-e",
        heuristic,
        "-n",
        str(walks),
        "-d",
        str(depth),
        "-s",
        str(stagnation),
    ]

    if seed is not None:
        cmd += ["--seed", str(seed)]

    cmd += [domain_file, problem_file]
    return cmd


def parse_plan_actions(stdout):
    actions = []

    for line in stdout.splitlines():
        match = PLAN_LINE_RE.match(line)
        if match:
            actions.append(" ".join(match.group("action").split()))

    return actions


def run_planner(cmd, timeout, debug=False):
    if debug:
        print("    $ " + " ".join(cmd))

    start = time.perf_counter()
    timed_out = False
    stdout = ""
    stderr = ""

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = error.stdout or ""
        stderr = error.stderr or ""

    elapsed = time.perf_counter() - start
    actions = parse_plan_actions(stdout)
    solved = (not timed_out) and len(actions) > 0

    if debug:
        print(f"    elapsed={elapsed:.2f}s timed_out={timed_out}")
        print("    ---- stdout ----")
        print(stdout[-3000:])
        if stderr.strip():
            print("    ---- stderr ----")
            print(stderr[-1500:])
        print(f"    parsed_actions={len(actions)}")

    return {
        "solved": solved,
        "timed_out": timed_out,
        "runtime_s": elapsed,
        "makespan": len(actions) if solved else None,
        "actions": actions,
        "stdout": stdout,
        "stderr": stderr,
    }


def validate_plan(val_bin, domain_file, problem_file, actions, debug=False):
    if not val_bin:
        return None

    if not actions:
        return False

    with tempfile.NamedTemporaryFile(mode="w", suffix=".plan", delete=False) as file:
        for action in actions:
            file.write(f"({action})\n")
        plan_path = file.name

    try:
        result = subprocess.run(
            [val_bin, domain_file, problem_file, plan_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        if debug:
            print("    ---- VAL output ----")
            print(output[-1500:])

        return ("Plan valid" in output) or ("Plan executed successfully" in output)
    except Exception as error:
        if debug:
            print(f"    VAL invocation failed: {error}")
        return None
    finally:
        os.unlink(plan_path)


def run_experiments(args):
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "results.csv"

    already_done = set()
    write_header = True

    if args.resume and csv_path.exists():
        with open(csv_path, newline="") as file:
            for row in csv.DictReader(file):
                already_done.add((row["domain"], row["problem_file"], row["planner"]))

        write_header = False
        print(f"[resume] {len(already_done)} run(s) already recorded")

    domains = ALL_DOMAINS if args.domain == "all" else [args.domain]
    mode = "a" if args.resume and csv_path.exists() else "w"

    with open(csv_path, mode, newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "domain",
                "problem_file",
                "planner",
                "solved",
                "timed_out",
                "runtime_s",
                "makespan",
                "valid",
            ],
        )

        if write_header:
            writer.writeheader()

        for domain in domains:
            problems = discover_problems(
                args.benchmarks,
                domain,
                args.max_problems,
                args.debug,
            )

            if not problems:
                print(f"[warn] no problems found for domain '{domain}'")
                continue

            for index, (domain_file, problem_file) in enumerate(problems, 1):
                print(f"[{domain}] ({index}/{len(problems)}) {os.path.basename(problem_file)}")

                for planner_name in ("HSP", "PRW"):
                    key = (domain, problem_file, planner_name)

                    if key in already_done:
                        print(f"    {planner_name}: skipped")
                        continue

                    if planner_name == "HSP":
                        cmd = build_hsp_command(
                            args.pddl4j_jar,
                            domain_file,
                            problem_file,
                            args.hsp_heuristic,
                            args.timeout,
                        )
                    else:
                        cmd = build_prw_command(
                            args.prw_classes,
                            args.pddl4j_jar,
                            domain_file,
                            problem_file,
                            args.timeout,
                            heuristic=args.prw_heuristic,
                            walks=args.prw_walks,
                            depth=args.prw_depth,
                            stagnation=args.prw_stagnation,
                            seed=args.prw_seed,
                        )

                    result = run_planner(cmd, args.timeout, args.debug)

                    valid = (
                        validate_plan(
                            args.val_bin,
                            domain_file,
                            problem_file,
                            result["actions"],
                            args.debug,
                        )
                        if result["solved"]
                        else None
                    )

                    print(
                        f"    {planner_name}: solved={result['solved']} "
                        f"time={result['runtime_s']:.2f}s "
                        f"makespan={result['makespan']} valid={valid}"
                    )

                    writer.writerow(
                        {
                            "domain": domain,
                            "problem_file": problem_file,
                            "planner": planner_name,
                            "solved": result["solved"],
                            "timed_out": result["timed_out"],
                            "runtime_s": f"{result['runtime_s']:.4f}",
                            "makespan": result["makespan"] if result["makespan"] is not None else "",
                            "valid": valid if valid is not None else "",
                        }
                    )

                    file.flush()

    print(f"\nDone. Raw results written to {csv_path}")
    return csv_path


def load_results(csv_path):
    rows = []

    with open(csv_path, newline="") as file:
        for row in csv.DictReader(file):
            row["runtime_s"] = float(row["runtime_s"]) if row["runtime_s"] else None
            row["makespan"] = int(row["makespan"]) if row["makespan"] else None
            rows.append(row)

    return rows


def summarize_results(rows):
    summary = {
        "HSP": {"solved": 0, "runtime": [], "makespan": []},
        "PRW": {"solved": 0, "runtime": [], "makespan": []},
    }

    for row in rows:
        planner = row["planner"]

        if row["solved"] == "True":
            summary[planner]["solved"] += 1

        if row["runtime_s"] is not None:
            summary[planner]["runtime"].append(row["runtime_s"])

        if row["makespan"] is not None:
            summary[planner]["makespan"].append(row["makespan"])

    lines = []

    for planner in ("HSP", "PRW"):
        runtimes = summary[planner]["runtime"]
        makespans = summary[planner]["makespan"]

        avg_runtime = sum(runtimes) / len(runtimes) if runtimes else None
        avg_makespan = sum(makespans) / len(makespans) if makespans else None

        lines.append(
            {
                "planner": planner,
                "solved": summary[planner]["solved"],
                "avg_runtime": avg_runtime,
                "avg_makespan": avg_makespan,
            }
        )

    return lines


def make_figures(csv_path, outdir, timeout, names, repo_url):
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    rows = load_results(csv_path)
    summary = summarize_results(rows)

    outdir = Path(outdir)
    pdf_path = outdir / "comparison_report.pdf"

    with PdfPages(pdf_path) as pdf:
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")

        ax.text(
            0.5,
            0.88,
            "HSP vs PRW Planner Comparison",
            ha="center",
            fontsize=20,
            weight="bold",
        )
        ax.text(
            0.5,
            0.82,
            "Benchmarks: blocksworld, depot, gripper, logistics",
            ha="center",
            fontsize=12,
        )
        ax.text(0.5, 0.72, "Students:", ha="center", fontsize=12, weight="bold")
        ax.text(0.5, 0.68, names, ha="center", fontsize=12)
        ax.text(0.5, 0.58, "Repository:", ha="center", fontsize=12, weight="bold")
        ax.text(0.5, 0.54, repo_url, ha="center", fontsize=10, color="blue")

        y = 0.42
        ax.text(0.5, y, "Overall Summary", ha="center", fontsize=14, weight="bold")
        y -= 0.05

        for item in summary:
            avg_runtime = (
                f"{item['avg_runtime']:.2f}s"
                if item["avg_runtime"] is not None
                else "n/a"
            )
            avg_makespan = (
                f"{item['avg_makespan']:.2f}"
                if item["avg_makespan"] is not None
                else "n/a"
            )

            ax.text(
                0.5,
                y,
                f"{item['planner']}: solved={item['solved']}, "
                f"avg runtime={avg_runtime}, avg makespan={avg_makespan}",
                ha="center",
                fontsize=11,
            )
            y -= 0.04

        ax.text(
            0.5,
            y - 0.04,
            "Lower runtime is better. Lower makespan means shorter plans.",
            ha="center",
            fontsize=10,
        )

        pdf.savefig(fig)
        plt.close(fig)

        for domain in ALL_DOMAINS:
            domain_rows = [row for row in rows if row["domain"] == domain]

            if not domain_rows:
                continue

            by_problem = {}

            for row in domain_rows:
                by_problem.setdefault(row["problem_file"], {})[row["planner"]] = row

            def sort_key(problem_file):
                hsp = by_problem[problem_file].get("HSP")

                if hsp and hsp["runtime_s"] is not None and hsp["solved"] == "True":
                    return (0, hsp["runtime_s"])

                return (1, 0)

            problem_files = sorted(by_problem.keys(), key=sort_key)
            labels = [os.path.basename(problem_file) for problem_file in problem_files]
            x_values = list(range(len(problem_files)))

            for metric, ylabel, filename in [
                ("runtime_s", "Runtime (s)", f"{domain}_runtime.png"),
                ("makespan", "Makespan (plan length)", f"{domain}_makespan.png"),
            ]:
                fig, ax = plt.subplots(figsize=(max(7, len(x_values) * 0.45), 4.8))

                for planner, marker, color in [
                    ("HSP", "o", "tab:blue"),
                    ("PRW", "s", "tab:orange"),
                ]:
                    xs = []
                    ys = []
                    timeout_xs = []

                    for x, problem_file in zip(x_values, problem_files):
                        row = by_problem[problem_file].get(planner)

                        if row is None:
                            continue

                        value = row[metric]

                        if value is not None:
                            xs.append(x)
                            ys.append(value)
                        elif row["timed_out"] == "True" and metric == "runtime_s":
                            timeout_xs.append(x)

                    ax.plot(xs, ys, marker=marker, color=color, label=planner)

                    if timeout_xs:
                        ax.scatter(
                            timeout_xs,
                            [timeout] * len(timeout_xs),
                            marker="x",
                            color=color,
                            s=60,
                            label=f"{planner} timeout",
                        )

                ax.set_title(f"{domain}: {ylabel}")
                ax.set_xlabel("Problem, ordered from simplest to hardest for HSP")
                ax.set_ylabel(ylabel)
                ax.set_xticks(x_values)
                ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
                ax.legend()
                fig.tight_layout()

                fig.savefig(outdir / filename, dpi=150)
                pdf.savefig(fig)
                plt.close(fig)

    print(f"Figures written to {outdir}/*.png")
    print(f"PDF report written to {pdf_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Compare HSP and PRW planners.")

    parser.add_argument("--pddl4j-jar", required=True)
    parser.add_argument("--prw-classes", required=True)
    parser.add_argument("--benchmarks", required=True)

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="per-planner timeout in seconds",
    )
    parser.add_argument("--outdir", default="results")

    parser.add_argument(
        "--hsp-heuristic",
        default="FAST_FORWARD",
        help="heuristic passed to HSP with -e",
    )

    parser.add_argument(
        "--prw-heuristic",
        default="FAST_FORWARD",
        help="heuristic passed to PRW with -e",
    )
    parser.add_argument(
        "--prw-walks",
        type=int,
        default=30,
        help="number of random walks passed to PRW with -n",
    )
    parser.add_argument(
        "--prw-depth",
        type=int,
        default=10,
        help="random walk depth passed to PRW with -d",
    )
    parser.add_argument(
        "--prw-stagnation",
        type=int,
        default=1,
        help="stagnation limit passed to PRW with -s",
    )
    parser.add_argument(
        "--prw-seed",
        type=int,
        default=None,
        help="optional random seed passed to PRW with --seed",
    )

    parser.add_argument(
        "--domain",
        choices=ALL_DOMAINS + ["all"],
        default="all",
    )
    parser.add_argument(
        "--max-problems",
        type=int,
        default=None,
        help="limit problems per domain for smoke tests",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print commands and planner output",
    )
    parser.add_argument(
        "--val-bin",
        default=None,
        help="path to VAL Validate executable",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip runs already present in results.csv",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="only regenerate figures from existing results.csv",
    )
    parser.add_argument(
        "--names",
        default="<student name 1>, <student name 2>",
        help="student names for the PDF report",
    )
    parser.add_argument(
        "--repo-url",
        default="<https://github.com/your-org/your-repo>",
        help="repository URL for the PDF report",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "results.csv"

    if not args.skip_run:
        csv_path = run_experiments(args)
    elif not csv_path.exists():
        print(f"--skip-run given but {csv_path} does not exist", file=sys.stderr)
        sys.exit(1)

    make_figures(csv_path, outdir, args.timeout, args.names, args.repo_url)


if __name__ == "__main__":
    main()