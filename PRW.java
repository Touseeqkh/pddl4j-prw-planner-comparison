package fr.uga.pddl4j.examples.prw;

import fr.uga.pddl4j.heuristics.state.StateHeuristic;
import fr.uga.pddl4j.parser.DefaultParsedProblem;
import fr.uga.pddl4j.plan.Plan;
import fr.uga.pddl4j.plan.SequentialPlan;
import fr.uga.pddl4j.planners.AbstractPlanner;
import fr.uga.pddl4j.planners.Planner;
import fr.uga.pddl4j.planners.PlannerConfiguration;
import fr.uga.pddl4j.planners.ProblemNotSupportedException;
import fr.uga.pddl4j.problem.DefaultProblem;
import fr.uga.pddl4j.problem.Problem;
import fr.uga.pddl4j.problem.State;
import fr.uga.pddl4j.problem.operator.Action;
import fr.uga.pddl4j.problem.operator.ConditionalEffect;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import picocli.CommandLine;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * PRW is a planner based on the "pure random walk" (PRW) procedure described
 * by Nakhost &amp; Muller in the Arvand planner (see
 * http://pddl4j.imag.fr/repository/exercices/resources/arvand.pdf).
 *
 * <p>The idea is simple and avoids building/maintaining a costly search tree:
 * from the current state we fire a batch of independent random walks of a
 * bounded length. Each walk applies a sequence of randomly chosen *applicable*
 * actions. We evaluate the heuristic value of the state reached by each walk
 * and keep the walk leading to the best (lowest) heuristic value. If that
 * value improves on our current best, we "commit" to that walk: its actions
 * are appended to the plan and the search continues from the resulting state.
 * If no walk improves the heuristic, we restart from the initial state
 * (classic restart strategy used to escape local minima / dead ends).</p>
 *
 * <p>This class follows exactly the structure used in the official PDDL4J
 * tutorial "Writing your own Planner" (see the ASP.java example), so that
 * the command line interface, statistics, and configuration mechanisms are
 * consistent with the rest of the library.</p>
 *
 * @author  (fill in your names here)
 * @version 1.0
 */
@CommandLine.Command(name = "PRW",
    version = "PRW 1.0",
    description = "Solves a specified planning problem using a pure random walk strategy "
        + "(Arvand-style Monte Carlo random walk planning).",
    sortOptions = false,
    mixinStandardHelpOptions = true,
    headerHeading = "Usage:%n",
    synopsisHeading = "%n",
    descriptionHeading = "%nDescription:%n%n",
    parameterListHeading = "%nParameters:%n",
    optionListHeading = "%nOptions:%n")
public class PRW extends AbstractPlanner {

    /**
     * The class logger.
     */
    private static final Logger LOGGER = LogManager.getLogger(PRW.class.getName());

    /* ------------------------------------------------------------------ *
     *  Configurable properties
     * ------------------------------------------------------------------ */

    /** Property name: number of random walks fired per iteration. */
    public static final String NUMBER_OF_WALKS_SETTING = "NUMBER_OF_WALKS";
    /** Default number of random walks fired per iteration. */
    public static final int DEFAULT_NUMBER_OF_WALKS = 30;

    /** Property name: length (max number of actions) of a single random walk. */
    public static final String WALK_LENGTH_SETTING = "WALK_LENGTH";
    /** Default walk length. */
    public static final int DEFAULT_WALK_LENGTH = 10;

    /** Property name: number of consecutive non-improving iterations before a restart. */
    public static final String MAX_STAGNATION_SETTING = "MAX_STAGNATION";
    /** Default stagnation threshold. */
    public static final int DEFAULT_MAX_STAGNATION = 1;

    /** Property name: heuristic used to evaluate the states reached by the walks. */
    public static final String HEURISTIC_SETTING = "HEURISTIC";
    /** Default heuristic. */
    public static final StateHeuristic.Name DEFAULT_HEURISTIC = StateHeuristic.Name.FAST_FORWARD;

    private int numberOfWalks;
    private int walkLength;
    private int maxStagnation;
    private StateHeuristic.Name heuristic;
    private long seed;

    /* ------------------------------------------------------------------ *
     *  Constructors
     * ------------------------------------------------------------------ */

    /**
     * Creates a new PRW planner with the default configuration.
     */
    public PRW() {
        this(PRW.getDefaultConfiguration());
    }

    /**
     * Creates a new PRW planner with a specified configuration.
     *
     * @param configuration the configuration of the planner.
     */
    public PRW(final PlannerConfiguration configuration) {
        super();
        this.setConfiguration(configuration);
    }

    /* ------------------------------------------------------------------ *
     *  Command line options
     * ------------------------------------------------------------------ */

    @CommandLine.Option(names = {"-n", "--walks"}, defaultValue = "30",
        paramLabel = "<walks>", description = "Number of random walks per iteration (preset 30).")
    public void setNumberOfWalks(final int n) {
        if (n <= 0) {
            throw new IllegalArgumentException("Number of walks <= 0");
        }
        this.numberOfWalks = n;
    }

    public final int getNumberOfWalks() {
        return this.numberOfWalks;
    }

    @CommandLine.Option(names = {"-d", "--depth"}, defaultValue = "10",
        paramLabel = "<depth>", description = "Length of a random walk (preset 10).")
    public void setWalkLength(final int l) {
        if (l <= 0) {
            throw new IllegalArgumentException("Walk length <= 0");
        }
        this.walkLength = l;
    }

    public final int getWalkLength() {
        return this.walkLength;
    }

    @CommandLine.Option(names = {"-s", "--stagnation"}, defaultValue = "1",
        paramLabel = "<stagnation>",
        description = "Number of non-improving iterations tolerated before a restart (preset 1).")
    public void setMaxStagnation(final int s) {
        if (s <= 0) {
            throw new IllegalArgumentException("Max stagnation <= 0");
        }
        this.maxStagnation = s;
    }

    public final int getMaxStagnation() {
        return this.maxStagnation;
    }

    @CommandLine.Option(names = {"-e", "--heuristic"}, defaultValue = "FAST_FORWARD",
        description = "Heuristic used to evaluate states reached by the walks: AJUSTED_SUM, "
            + "AJUSTED_SUM2, AJUSTED_SUM2M, COMBO, MAX, FAST_FORWARD, SET_LEVEL, SUM, "
            + "SUM_MUTEX (preset: FAST_FORWARD)")
    public void setHeuristic(final StateHeuristic.Name heuristic) {
        this.heuristic = heuristic;
    }

    public final StateHeuristic.Name getHeuristic() {
        return this.heuristic;
    }

    @CommandLine.Option(names = {"--seed"}, defaultValue = "0",
        description = "Seed of the pseudo random number generator (preset 0, i.e. non reproducible).")
    public void setSeed(final long seed) {
        this.seed = seed;
    }

    public final long getSeed() {
        return this.seed;
    }

    /* ------------------------------------------------------------------ *
     *  AbstractPlanner overrides
     * ------------------------------------------------------------------ */

    @Override
    public Problem instantiate(final DefaultParsedProblem problem) {
        final Problem pb = new DefaultProblem(problem);
        pb.instantiate();
        return pb;
    }

    /**
     * Pure random walk search. See class header for the algorithm description.
     *
     * @param problem the problem to solve.
     * @return the plan found or null if no plan was found within the timeout.
     */
    @Override
    public Plan solve(final Problem problem) {
        LOGGER.info("* Starting pure random walk search\n");
        final long begin = System.currentTimeMillis();
        Plan plan = null;
        try {
            plan = this.pureRandomWalk(problem);
        } catch (ProblemNotSupportedException e) {
            LOGGER.fatal(e.getMessage());
        }
        final long end = System.currentTimeMillis();
        if (plan != null) {
            LOGGER.info("* Pure random walk search succeeded\n");
            this.getStatistics().setTimeToSearch(end - begin);
        } else {
            LOGGER.info("* Pure random walk search failed\n");
        }
        return plan;
    }

    /**
     * Returns true only for STRIPS/typed problems without numeric fluents, durative
     * actions, etc. Adapt this if your planner needs to support a richer subset of PDDL.
     *
     * @param problem the problem to test.
     * @return true if the problem is supported by this planner.
     */
    @Override
    public boolean isSupported(final Problem problem) {
        return true;
    }

    /* ------------------------------------------------------------------ *
     *  Core algorithm
     * ------------------------------------------------------------------ */

    /**
     * Runs the pure random walk procedure.
     *
     * @param problem the instantiated problem.
     * @return a sequential plan solving the problem, or null if the timeout is reached
     *     before a solution is found.
     * @throws ProblemNotSupportedException if the problem is not supported.
     */
    private Plan pureRandomWalk(final Problem problem) throws ProblemNotSupportedException {
        if (!this.isSupported(problem)) {
            throw new ProblemNotSupportedException("Problem not supported");
        }

        final StateHeuristic h = StateHeuristic.getInstance(this.getHeuristic(), problem);
        final Random rng = this.getSeed() == 0 ? new Random() : new Random(this.getSeed());

        final State init = new State(problem.getInitialState());

        // currentPlan stores the *indices* of the actions chosen so far, in order.
        List<Integer> currentPlan = new ArrayList<>();
        State current = new State(init);
        double currentHeuristic = h.estimate(current, problem.getGoal());

        final long timeout = this.getTimeout() * 1000L;
        final long start = System.currentTimeMillis();
        int stagnation = 0;

        while (!current.satisfy(problem.getGoal())
                && System.currentTimeMillis() - start < timeout) {

            List<Integer> bestWalkActions = null;
            State bestWalkState = null;
            double bestWalkHeuristic = Double.POSITIVE_INFINITY;

            // Fire numberOfWalks independent random walks from the current state.
            for (int w = 0; w < this.getNumberOfWalks(); w++) {
                final List<Integer> walkActions = new ArrayList<>();
                final State walkState = this.randomWalk(current, problem, this.getWalkLength(), rng, walkActions);
                // A walk that reaches the goal is immediately the best possible outcome.
                if (walkState.satisfy(problem.getGoal())) {
                    bestWalkActions = walkActions;
                    bestWalkState = walkState;
                    bestWalkHeuristic = 0;
                    break;
                }
                final double walkHeuristic = h.estimate(walkState, problem.getGoal());
                if (walkHeuristic < bestWalkHeuristic) {
                    bestWalkHeuristic = walkHeuristic;
                    bestWalkActions = walkActions;
                    bestWalkState = walkState;
                }
            }

            if (bestWalkHeuristic < currentHeuristic) {
                // Commit to the best walk found: move the search frontier forward.
                currentPlan.addAll(bestWalkActions);
                current = bestWalkState;
                currentHeuristic = bestWalkHeuristic;
                stagnation = 0;
            } else {
                stagnation++;
                if (stagnation >= this.getMaxStagnation()) {
                    // Local minimum / dead end: restart from the initial state.
                    LOGGER.debug("* Restarting from initial state (stagnation reached)\n");
                    currentPlan = new ArrayList<>();
                    current = new State(init);
                    currentHeuristic = h.estimate(current, problem.getGoal());
                    stagnation = 0;
                }
            }
        }

        if (!current.satisfy(problem.getGoal())) {
            return null;
        }

        final Plan plan = new SequentialPlan();
        for (final Integer actionIndex : currentPlan) {
            plan.add(plan.size(), problem.getActions().get(actionIndex));
        }
        return plan;
    }

    /**
     * Performs one random walk of at most {@code length} steps from {@code from}.
     * At each step an action is picked uniformly at random among the actions
     * applicable in the current state of the walk. The walk stops early if a dead
     * end is reached (no applicable action) or if the goal is satisfied.
     *
     * @param from         the state the walk starts from (not modified).
     * @param problem      the problem (used to access the action set and the goal).
     * @param length       the maximum length of the walk.
     * @param rng          the pseudo random number generator to use.
     * @param actionsTaken an (initially empty) list that will be filled, in order,
     *                     with the indices of the actions applied during the walk.
     * @return the state reached at the end of the walk.
     */
    private State randomWalk(final State from, final Problem problem, final int length,
                              final Random rng, final List<Integer> actionsTaken) {
        final State current = new State(from);
        final List<Action> actions = problem.getActions();

        for (int step = 0; step < length; step++) {
            final List<Integer> applicable = new ArrayList<>();
            for (int i = 0; i < actions.size(); i++) {
                if (actions.get(i).isApplicable(current)) {
                    applicable.add(i);
                }
            }
            if (applicable.isEmpty()) {
                // Dead end: stop the walk here.
                break;
            }
            final int chosen = applicable.get(rng.nextInt(applicable.size()));
            final Action action = actions.get(chosen);
            for (final ConditionalEffect ce : action.getConditionalEffects()) {
                if (current.satisfy(ce.getCondition())) {
                    current.apply(ce.getEffect());
                }
            }
            actionsTaken.add(chosen);
            if (current.satisfy(problem.getGoal())) {
                break;
            }
        }
        return current;
    }

    /* ------------------------------------------------------------------ *
     *  Configuration plumbing (mirrors the official ASP.java example)
     * ------------------------------------------------------------------ */

    @Override
    public PlannerConfiguration getConfiguration() {
        final PlannerConfiguration config = super.getConfiguration();
        config.setProperty(PRW.NUMBER_OF_WALKS_SETTING, Integer.toString(this.getNumberOfWalks()));
        config.setProperty(PRW.WALK_LENGTH_SETTING, Integer.toString(this.getWalkLength()));
        config.setProperty(PRW.MAX_STAGNATION_SETTING, Integer.toString(this.getMaxStagnation()));
        config.setProperty(PRW.HEURISTIC_SETTING, this.getHeuristic().toString());
        return config;
    }

    @Override
    public void setConfiguration(final PlannerConfiguration configuration) {
        super.setConfiguration(configuration);
        this.setNumberOfWalks(configuration.getProperty(PRW.NUMBER_OF_WALKS_SETTING) == null
            ? PRW.DEFAULT_NUMBER_OF_WALKS
            : Integer.parseInt(configuration.getProperty(PRW.NUMBER_OF_WALKS_SETTING)));
        this.setWalkLength(configuration.getProperty(PRW.WALK_LENGTH_SETTING) == null
            ? PRW.DEFAULT_WALK_LENGTH
            : Integer.parseInt(configuration.getProperty(PRW.WALK_LENGTH_SETTING)));
        this.setMaxStagnation(configuration.getProperty(PRW.MAX_STAGNATION_SETTING) == null
            ? PRW.DEFAULT_MAX_STAGNATION
            : Integer.parseInt(configuration.getProperty(PRW.MAX_STAGNATION_SETTING)));
        this.setHeuristic(configuration.getProperty(PRW.HEURISTIC_SETTING) == null
            ? PRW.DEFAULT_HEURISTIC
            : StateHeuristic.Name.valueOf(configuration.getProperty(PRW.HEURISTIC_SETTING)));
    }

    /**
     * Returns the default configuration of the PRW planner.
     *
     * @return the default configuration of the PRW planner.
     */
    public static PlannerConfiguration getDefaultConfiguration() {
        final PlannerConfiguration config = Planner.getDefaultConfiguration();
        config.setProperty(PRW.NUMBER_OF_WALKS_SETTING, Integer.toString(PRW.DEFAULT_NUMBER_OF_WALKS));
        config.setProperty(PRW.WALK_LENGTH_SETTING, Integer.toString(PRW.DEFAULT_WALK_LENGTH));
        config.setProperty(PRW.MAX_STAGNATION_SETTING, Integer.toString(PRW.DEFAULT_MAX_STAGNATION));
        config.setProperty(PRW.HEURISTIC_SETTING, PRW.DEFAULT_HEURISTIC.toString());
        return config;
    }

    @Override
    public boolean hasValidConfiguration() {
        return super.hasValidConfiguration()
            && this.getNumberOfWalks() > 0
            && this.getWalkLength() > 0
            && this.getMaxStagnation() > 0
            && this.getHeuristic() != null;
    }

    /* ------------------------------------------------------------------ *
     *  Entry point
     * ------------------------------------------------------------------ */

    /**
     * The main method of the <code>PRW</code> planner.
     *
     * @param args the arguments of the command line.
     */
    public static void main(final String[] args) {
        try {
            final PRW planner = new PRW();
            final CommandLine cmd = new CommandLine(planner);
            cmd.execute(args);
        } catch (IllegalArgumentException e) {
            LOGGER.fatal(e.getMessage());
        }
    }
}