# Operations Labor Capacity Optimization (LP)

An end-to-end Operations Research and Capacity Planning pipeline that uses Mixed-Integer Linear Programming (MILP) to generate an optimal, cost-efficient labor schedule. 

This project simulates a highly volatile logistics environment where bulk inventory deliveries cause massive spikes in labor demand. The Python-based optimization engine calculates the exact number of Full-Time and Part-Time shifts required to cover demand without violating corporate stability policies, and automatically exports a multi-sheet, formatted Excel dashboard for operations managers. The model is built dynamically, allowing stakeholders to adjust business parameters (such as wage rates or part-time ratios) at the start to instantly generate updated, fully optimized schedules and financial breakdowns.

## The Operational Problem
Warehouses utilizing Economic Order Quantity (EOQ) inventory models often face severe capacity planning challenges. Instead of a steady flow of daily trucks, they receive massive bulk shipments on random days, causing labor demand to spike by up to 250%. 

Relying entirely on Full-Time (FT) staff leads to expensive overstaffing on quiet days. Relying entirely on Part-Time (PT) staff violates operational stability and union policies. 

**The objective:** Minimize total payroll costs while guaranteeing 100% of the required labor demand is met, ensuring that PT labor never exceeds 35% of total scheduled hours.

## The Mathematical Engine (Linear Programming)
This model operates at the **Capacity Planning (Shift Generation)** level. It determines the optimal aggregate pool of 8-hour and 4-hour time blocks needed. 

The engine uses the `PuLP` library to solve the following constraints:

**Decision Variables:**
* $F_t$ = Number of FT shifts (8-hour) starting at time block $t$.
* $P_t$ = Number of PT shifts (4-hour) starting at time block $t$.
* $D_t$ = Required staff demand for time block $t$.

**Objective (Minimize Total Wages):**

$$ \min \sum_{t=1}^{84} (200 F_t + 72 P_t) $$

**Constraints:**
1. **Demand Satisfaction:** Active workers (FT starting now + FT continuing from last block + PT starting now) must meet or exceed required demand.

$$ F_t + F_{t-1} + P_t \ge D_t \quad \forall t $$

2. **Operational Part-Time Cap:** Part-time hours cannot exceed 35% of total hours worked.

$$ \sum_{t=1}^{84} 4 P_t \le 0.35 \left( \sum_{t=1}^{84} (8 F_t + 4 P_t) \right) $$

## Project Pipeline (4 Phases)

1. **Parameter Ingestion:** Python checks for a `Warehouse_Parameters.xlsx` file. If none exists, it generates baseline business rules (wage rates, PT ratio caps, shift lengths). If a stakeholder updates the Excel file, the Python engine dynamically recalculates the entire linear programming model.
2. **Demand Simulation:** Generates a 14-day schedule (84 4-hour blocks) with baseline demand, randomly injecting 250% EOQ delivery spikes to stress-test the algorithm.
3. **MILP Optimization (`PuLP`):** Solves the 168-variable mathematical puzzle to find the absolute mathematical minimum cost. Translates raw shifts into actionable capacity planning goals.
4. **Automated Excel Dashboarding:** Uses `pandas` and `openpyxl` to write the optimal schedule and executive summary back into a formatted, multi-sheet Excel file, embedding Matplotlib/Seaborn visualization charts directly into the spreadsheets.

## Visual Outputs
*<img width="1402" height="371" alt="image" src="https://github.com/user-attachments/assets/6e675c75-d4c6-42a3-bc88-c978ccdb0596" />*
*<img width="1584" height="584" alt="image" src="https://github.com/user-attachments/assets/7422bad2-ef72-4e10-afe1-2b3f2d9d4429" />*

## Tech Stack
* **Python** (Core Logic)
* **PuLP** (Mixed-Integer Linear Programming Engine)
* **Pandas** (Data Manipulation & Pipeline)
* **Matplotlib / Seaborn** (Data Visualization)
* **OpenPyXL** (Automated Excel Formatting & Image Embedding)

## How to Run
1. Clone the repository.
2. Install dependencies: `pip install pandas numpy pulp matplotlib seaborn openpyxl`
3. Run the Jupyter Notebook from top to bottom.
4. Modify `Warehouse_Parameters.xlsx` and re-run to see the MILP engine dynamically adapt to new business inputs!
