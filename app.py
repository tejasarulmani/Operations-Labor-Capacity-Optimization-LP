import streamlit as st
import pandas as pd
import numpy as np
import pulp
import math
import matplotlib.pyplot as plt
import seaborn as sns
import os
from io import BytesIO
from openpyxl.drawing.image import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Warehouse Capacity Optimizer", layout="wide")
st.title("Warehouse Operations & Capacity Optimization")
st.markdown("""
This tool uses Mixed-Integer Linear Programming (MILP) to generate the lowest-cost labor schedule during highly volatile EOQ delivery spikes. 
Adjust your business parameters on the left to instantly generate an optimal 14-day schedule.
""")

# --- SIDEBAR: DYNAMIC INPUTS ---
st.sidebar.header("1. Business Parameters")
st.sidebar.markdown("Adjust the values below to update the model constraints.")

# Interactive web app inputs with default values
ft_wage_per_hour = st.sidebar.number_input("Full-Time Wage ($/hr)", min_value=10.0, max_value=100.0, value=25.0, step=1.0)
pt_wage_per_hour = st.sidebar.number_input("Part-Time Wage ($/hr)", min_value=10.0, max_value=100.0, value=18.0, step=1.0)
max_pt_ratio = st.sidebar.slider("Max Part-Time Ratio", min_value=0.0, max_value=1.0, value=0.35, step=0.05)
ft_shift_hours = st.sidebar.number_input("FT Shift Length (hours)", min_value=4, max_value=12, value=8, step=1)
pt_shift_hours = st.sidebar.number_input("PT Shift Length (hours)", min_value=2, max_value=8, value=4, step=1)

# Calculate per-shift wages dynamically based on the inputs
ft_wage_per_shift = ft_wage_per_hour * ft_shift_hours
pt_wage_per_shift = pt_wage_per_hour * pt_shift_hours

# --- BUTTON TO RUN OPTIMIZATION ---
if st.button("Run Optimization Engine", type="primary"):
    with st.spinner("Simulating demand and optimizing schedule via PuLP..."):
        
        # --- PHASE 2: DEMAND SIMULATION ---
        num_days = 14
        blocks_per_day = 6
        baseline_demand = np.random.randint(5, 11, size=(num_days, blocks_per_day))
        eoq_delivery_days_indices = np.random.choice(num_days, 4, replace=False)
        
        for day_index in eoq_delivery_days_indices:
            baseline_demand[day_index, :] = np.ceil(baseline_demand[day_index, :] * 2.5)

        data = []
        for day in range(num_days):
            for block in range(blocks_per_day):
                data.append({'Day': day + 1, 'Block': block + 1, 'Demand': int(baseline_demand[day, block])})
        demand_df = pd.DataFrame(data)

        # --- PHASE 3A: MILP OPTIMIZATION ---
        num_blocks = len(demand_df)
        prob = pulp.LpProblem("Warehouse_Workforce_Optimization", pulp.LpMinimize)

        FT = pulp.LpVariable.dicts("FT", range(num_blocks), lowBound=0, cat='Integer')
        PT = pulp.LpVariable.dicts("PT", range(num_blocks), lowBound=0, cat='Integer')

        prob += pulp.lpSum([ft_wage_per_shift * FT[t] + pt_wage_per_shift * PT[t] for t in range(num_blocks)]), "Total_Cost"

        for t in range(num_blocks):
            required_staff = demand_df.loc[t, 'Demand']
            if t % blocks_per_day == 0:
                prob += FT[t] + PT[t] >= required_staff
            else:
                prob += FT[t] + FT[t-1] + PT[t] >= required_staff

        total_pt_hours = pulp.lpSum([PT[t] * pt_shift_hours for t in range(num_blocks)])
        total_ft_hours = pulp.lpSum([FT[t] * ft_shift_hours for t in range(num_blocks)])
        total_hours_worked = total_pt_hours + total_ft_hours
        
        prob += total_pt_hours <= max_pt_ratio * total_hours_worked, "HR_Part_Time_Cap"

        prob.solve()

        demand_df['FT_Start'] = [int(FT[t].varValue) if FT[t].varValue is not None else 0 for t in range(num_blocks)]
        demand_df['PT_Start'] = [int(PT[t].varValue) if PT[t].varValue is not None else 0 for t in range(num_blocks)]

        total_active_workers = []
        for t in range(num_blocks):
            ft_current_start = demand_df.loc[t, 'FT_Start']
            if t % blocks_per_day == 0:
                ft_previous_start = 0
            else:
                ft_previous_start = demand_df.loc[t-1, 'FT_Start']
            pt_current_start = demand_df.loc[t, 'PT_Start']
            
            total_active_workers.append(ft_current_start + ft_previous_start + pt_current_start)

        demand_df['Total_Active'] = total_active_workers
        demand_df['Overstaffed_By'] = demand_df['Total_Active'] - demand_df['Demand']

        # --- PHASE 3B: EXECUTIVE SUMMARY ---
        total_ft_shifts = demand_df['FT_Start'].sum()
        total_pt_shifts = demand_df['PT_Start'].sum()
        total_shifts = total_ft_shifts + total_pt_shifts
        
        ft_total_cost = total_ft_shifts * ft_wage_per_shift
        pt_total_cost = total_pt_shifts * pt_wage_per_shift
        grand_total_cost = ft_total_cost + pt_total_cost

        ft_headcount = math.ceil(total_ft_shifts / 10)
        pt_headcount = math.ceil(total_pt_shifts / 10)
        total_headcount = ft_headcount + pt_headcount

        summary_data = {
            'Metric': ['Total FT Shifts', 'Total PT Shifts', 'Total Shifts', 'Total FT Wage Cost', 'Total PT Wage Cost', 'Grand Total Cost', 'FT Headcount', 'PT Headcount', 'Total Headcount'],
            'Value': [f"{total_ft_shifts:.0f}", f"{total_pt_shifts:.0f}", f"{total_shifts:.0f}", f"${ft_total_cost:,.2f}", f"${pt_total_cost:,.2f}", f"${grand_total_cost:,.2f}", f"{ft_headcount:.0f} workers", f"{pt_headcount:.0f} workers", f"{total_headcount:.0f} workers"]
        }
        executive_summary_df = pd.DataFrame(summary_data)

        # --- DISPLAY RESULTS ON WEB APP ---
        st.success(f"Optimization Complete. Mathematical Status: {pulp.LpStatus[prob.status]}")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Executive HR Summary")
            st.dataframe(executive_summary_df, use_container_width=True)
        with col2:
            st.subheader("Generated 14-Day Schedule")
            st.dataframe(demand_df, height=350, use_container_width=True)

        # --- CHARTS ---
        st.subheader("Visual Analytics")
        
        # Coverage Chart
        fig_cov = plt.figure(figsize=(16, 6))
        sns.set_theme(style="whitegrid")
        plt.fill_between(demand_df.index, demand_df['Total_Active'], color='skyblue', alpha=0.6, label='Scheduled Workers (Active)')
        plt.plot(demand_df.index, demand_df['Demand'], color='red', linestyle='--', linewidth=2.5, label='Required Demand')
        plt.title('Warehouse Workforce Optimization: Scheduled vs. Required (14-Day Cycle)', fontsize=16, fontweight='bold')
        plt.xlabel('Time Blocks (84 Total)', fontsize=12)
        plt.ylabel('Number of Workers', fontsize=12)
        plt.legend(loc='upper right', fontsize=12)
        plt.xlim(0, num_blocks - 1)
        plt.tight_layout()
        plt.savefig('coverage_chart.png', bbox_inches='tight')
        st.pyplot(fig_cov)

        # Headcount & Cost Charts
        fig_hr, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 4))
        colors = ['#2c3e50', '#e74c3c']
        
        ax1.pie([ft_headcount, pt_headcount], labels=['FT Workers', 'PT Workers'], colors=colors, autopct=lambda p: '{:.0f}'.format(p * total_headcount / 100), startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
        ax1.add_artist(plt.Circle((0,0), 0.70, fc='white'))
        ax1.text(0, 0, f'Total\n{total_headcount}', ha='center', va='center', fontsize=14, fontweight='bold')
        ax1.set_title('Required Headcount Breakdown', fontsize=14, fontweight='bold')

        ax2.barh([0], ft_total_cost, color=colors[0], edgecolor='white', height=0.4, label='FT Cost')
        ax2.barh([0], pt_total_cost, left=ft_total_cost, color=colors[1], edgecolor='white', height=0.4, label='PT Cost')
        ax2.text(ft_total_cost / 2, 0, f'FT Cost: ${ft_total_cost:,.0f}', ha='center', va='center', color='white', fontsize=11, fontweight='bold')
        ax2.text(ft_total_cost + (pt_total_cost / 2), 0, f'PT Cost: ${pt_total_cost:,.0f}', ha='center', va='center', color='white', fontsize=11, fontweight='bold')
        ax2.set_yticks([]) 
        ax2.set_xlim(0, grand_total_cost)
        ax2.set_xlabel('Total Payroll Cost ($)', fontsize=12)
        ax2.set_title('Payroll Cost Breakdown', fontsize=14, fontweight='bold')
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2)
        
        plt.tight_layout()
        plt.savefig('hr_charts.png', bbox_inches='tight')
        st.pyplot(fig_hr)

        # --- PHASE 4: EXCEL EXPORT (IN-MEMORY) ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            executive_summary_df.to_excel(writer, sheet_name='HR_Summary', index=False)
            demand_df.to_excel(writer, sheet_name='Optimized_Schedule', index=False)
            
            # Auto-adjust column widths
            for sheet_name in ['HR_Summary', 'Optimized_Schedule']:
                sheet = writer.sheets[sheet_name]
                for column in sheet.columns:
                    max_length = max((len(str(cell.value)) for cell in column if cell.value), default=0)
                    sheet.column_dimensions[column[0].column_letter].width = (max_length + 2) * 1.2
            
            # Embed charts using the locally saved PNG files
            if os.path.exists('hr_charts.png'):
                writer.sheets['HR_Summary'].add_image(Image('hr_charts.png'), 'D2')
            if os.path.exists('coverage_chart.png'):
                writer.sheets['Optimized_Schedule'].add_image(Image('coverage_chart.png'), 'K2')

        st.divider()
        st.subheader("Export Results")
        st.download_button(
            label="Download Automated Excel Dashboard",
            data=output.getvalue(),
            file_name="Optimized_Warehouse_Schedule.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )