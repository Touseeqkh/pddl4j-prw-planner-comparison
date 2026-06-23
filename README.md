\# HSP vs Pure Random Walk Planner Comparison in PDDL4J



Students: REAL NAME 1, REAL NAME 2  

Repository: YOUR REAL GITHUB URL



\## 1. Project Overview



This project was completed for an automated planning assignment using the PDDL4J library.



The goal of the assignment was to implement a custom planner in Java using PDDL4J and compare its performance with the built-in HSP planner. The custom planner uses a Pure Random Walk planning procedure inspired by the Arvand paper.



The project includes:



\- a Java implementation of a Pure Random Walk planner

\- a Python script for comparing planners

\- experiment results on four benchmark domains

\- figures for runtime and makespan

\- a PDF report containing the final comparison



\## 2. PDDL4J Library



PDDL4J is an open source Java library for automated planning based on PDDL, the Planning Domain Definition Language.



PDDL is a standard language used to describe planning domains and planning problems. It is widely used in automated planning research because it allows planners to be compared on common benchmark problems.



PDDL4J provides:



\- a PDDL parser

\- an HDDL parser

\- tools for representing planning domains and problems

\- preprocessing and grounding mechanisms

\- classical planning heuristics

\- example planners such as HSP and FastForward



This project uses PDDL4J to parse PDDL benchmark problems, instantiate planning tasks, and run both the built-in HSP planner and the custom Pure Random Walk planner.



\## 3. Assignment Goal



The assignment required the following:



1\. Implement a custom planner in Java using PDDL4J.

2\. Follow the PDDL4J tutorial section "Implement your own planner".

3\. Implement a planning procedure based on Pure Random Walks.

4\. Compare the custom planner with HSP, the PDDL4J A\* planner.

5\. Use four benchmark domains:

&#x20;  - blocksworld

&#x20;  - depot

&#x20;  - gripper

&#x20;  - logistics

6\. Measure two metrics:

&#x20;  - total runtime

&#x20;  - makespan, meaning the number of actions in the plan

7\. Generate eight figures:

&#x20;  - runtime figure for each domain

&#x20;  - makespan figure for each domain

8\. Include the script and results in a GitHub repository.

9\. Include a PDF report with student names and repository link.



\## 4. Implemented Planners



\### 4.1 HSP



HSP is the reference planner used for comparison.



It is the built-in PDDL4J heuristic state-space planner. It uses A\* search with a heuristic function.



In this project, HSP is called from the comparison script and used as the baseline planner.



\### 4.2 Pure Random Walk Planner



The custom planner is a Pure Random Walk planner implemented in Java.



The planner repeatedly performs random walks from a planning state. During each walk, it randomly chooses applicable actions and moves through the state space. The search continues until a goal state is found, the stagnation condition is reached, or the timeout is exceeded.



The planner exposes several parameters:



\- `-n`: number of random walks

\- `-d`: maximum depth of each walk

\- `-s`: stagnation limit

\- `--seed`: optional random seed for reproducible results

\- `-e`: heuristic used to evaluate states

\- `-t`: timeout in seconds



The planner is located in the Java source code as:



```text

fr.uga.pddl4j.examples.prw.PRW

