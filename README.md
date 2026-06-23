# HSP vs Pure Random Walk Planner Comparison in PDDL4J

**Student:** Touseeq Danish  
**Email:** touseeqbalouch@gmail.com  
**Repository:** https://github.com/Touseeqkh/pddl4j-prw-planner-comparison

---

## 1. Project Overview

This project was developed as part of an automated planning assignment using the **PDDL4J library**.

The objective was to implement a custom planner in Java and compare its performance against the built-in **HSP (Heuristic State Space Planner)**.

The custom planner is based on a **Pure Random Walk (PRW)** strategy inspired by stochastic search methods used in classical planning research (e.g., Arvand-style planning).

The project evaluates both planners across standard benchmark domains and analyzes their performance in terms of runtime and solution quality.

---

## 2. PDDL4J Library

**PDDL4J** is an open-source Java library for automated planning based on the Planning Domain Definition Language (PDDL).

PDDL is widely used in AI planning research to describe:

- Planning domains (actions, predicates, and rules)
- Planning problems (initial states and goal states)

PDDL4J provides:

- A PDDL parser and problem instantiation tools
- Grounding and preprocessing utilities
- State-space search infrastructure
- Classical planning heuristics (e.g., Fast Forward heuristic)
- Reference planners such as HSP

This project uses PDDL4J to:

- Parse benchmark planning problems
- Instantiate planning states
- Execute both HSP and the custom PRW planner
- Evaluate performance across multiple domains

---

## 3. Assignment Objectives

The assignment required the following:

1. Implement a custom planner in Java using PDDL4J
2. Follow the PDDL4J tutorial: *“Implement your own planner”*
3. Design a **Pure Random Walk-based planning algorithm**
4. Compare performance with the built-in **HSP planner**
5. Evaluate on four benchmark domains:
   - Blocksworld
   - Depot
   - Gripper
   - Logistics
6. Measure performance using:
   - Runtime (seconds)
   - Makespan (number of actions in the plan)
7. Generate experimental plots:
   - Runtime per domain
   - Makespan per domain
8. Produce a reproducible GitHub repository with scripts and results
9. Provide a final PDF report with results and analysis

---

## 4. Implemented Planners

### 4.1 HSP Planner (Baseline)

HSP (Heuristic State-space Planner) is the baseline planner provided by PDDL4J.

It uses:

- Heuristic-guided A* search
- Fast Forward heuristic (`FAST_FORWARD`)
- Deterministic state-space exploration

HSP is used as the reference system for evaluating the quality of the custom planner.

---

### 4.2 Pure Random Walk (PRW) Planner

The custom planner implements a **Pure Random Walk (PRW)** strategy.

Instead of systematically exploring a search tree, the planner:

- Generates multiple random walks from the current state
- Each walk applies randomly selected applicable actions
- Evaluates resulting states using a heuristic function
- Selects the best-performing walk
- Commits to that path if it improves the current solution
- Restarts when stagnation occurs

This process continues until:

- A goal state is reached, or  
- A timeout occurs

---

### Key Parameters

The planner supports the following configuration options:

- `-n` / `--walks`  
  Number of random walks per iteration

- `-d` / `--depth`  
  Maximum depth of each random walk

- `-s` / `--stagnation`  
  Number of non-improving iterations before restart

- `--seed`  
  Random seed for reproducibility

- `-e` / `--heuristic`  
  Heuristic used for evaluation (default: FAST_FORWARD)

- `-t`  
  Timeout per problem instance (in seconds)

---

### Implementation Location

The PRW planner is implemented in:

```text
src/main/java/fr/uga/pddl4j/examples/prw/PRW.java
