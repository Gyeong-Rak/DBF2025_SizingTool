import numpy as np
import math
import matplotlib.pyplot as plt
from scipy.optimize import fsolve
from scipy.interpolate import interp1d
import pandas as pd

""" constants """
## Constant values
g = 9.81        
rho = 1.20     

""" variable from previous block """ 
## Values below are the example (should be removed)

# Values from sizing tool
m_total = 8.5       # total takeoff weight(kg)
m_x1 = 0.2          # X-1 test vehicle weight(kg)

# Values from aerodynamic analysis block
alpha_result = [-3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0]

CL_result  = [-0.222436413643, -0.180875576755, -0.139353137812, -0.096288694512, -0.052894264361, -0.010754747321, 0.03419869168, 0.078854413452, 0.12106696648, 0.161467678137, 0.201566908973, 0.241976026112, 0.283543470056, 0.325138093932, 0.366766152143, 0.408601633264, 0.450967415346, 0.492989122636, 0.53524722748, 0.577778950465, 0.620252144137, 0.66246540482, 0.704655611664, 0.746793179114, 0.789031485863, 0.831251673013, 0.873484864926, 0.915483050867, 0.957648958944, 0.999516432639, 1.041274666905, 1.083247121776, 1.125457607853, 1.167900194023]

CD_result = [0.061772973184999996, 0.060765457993, 0.059979766333, 0.059394043367, 0.059040664995, 0.058869576359, 0.058963513243, 0.059280045015, 0.059776186698, 0.060453351271999994, 0.061323192485999996, 0.062396026167, 0.063704602328, 0.06522873753899999, 0.066964071138, 0.068919968281, 0.071116570998, 0.07350985547899999, 0.07612991908899999, 0.078985169342, 0.082052402645, 0.085314783391, 0.088788471021, 0.09247106842200001, 0.096374377045, 0.100489297343, 0.104817307711, 0.109328470074, 0.114072939519, 0.11898399017, 0.124117963712, 0.129468159746, 0.13505869094099998, 0.14089597807600002]

CL_max = 0.94           # maximum lift coefficient
CL_max_flap = 1.1       # maximum lift coefficient with flap deploy
CD_max_flap = 0.20      # maximum drag coefficient with flap deploy
CL_zero_flap = 0.04     # 0 AOA lift coefficient with flap deploy
CD_zero_flap = 0.10    # 0 AOA drag coefficient with flap deploy

# # Values from aerodynamic analysis block
# csv_path = r"C:\Users\ksjsms\2025\AIAA\OpenVSP_ws\analysis_results\aero_result_span_1800.csv"
# df = pd.read_csv(csv_path)
# alpha_result = df["Alpha (deg)"].to_numpy()
# CL_result    = df["C_L"].to_numpy() 
# CD_result    = df["C_Dtot"].to_numpy()

# Values from sizing parameter
m_empty = 5.0       # empty weight(kg) 
S = 0.6             # wing area(m^2)
AR = 5.4            # wing aspect ratio    
lw = -36.192786918391576          # Distance from the aircraft's CG to the main wing AC (m)
lh = 852.8685720200021           # Distance from the aircraft's CG to the Horizontal Tail AC (m)


# Values from propulsion block
T_max_kg = 6.6      # Total maximum thrust generated by all motors (kg)
initial_battery_capacity = 2250.0 # mAh (milliamp-hours) (per one battery)
minimum_battery_voltage = 20 # V (원래는 3 x 6 = 18 V 인데 안전하게 20 V)
propulsion_efficiency = 0.8 # Efficiency of the propulsion system

# read data
Batt_file_path = r"2.25Ah Discharge Profile.csv"
df = pd.read_csv(Batt_file_path, skiprows=17, on_bad_lines='skip') 
df.columns = ["Test", "Time (s)", "Voltage (V)", "Current", "Temp (F)"]

df["Time (s)"] = pd.to_numeric(df["Time (s)"], errors='coerce')
df["Voltage (V)"] = pd.to_numeric(df["Voltage (V)"], errors='coerce')
df["Current"] = pd.to_numeric(df["Current"], errors='coerce')

# SOC(State of Charge)
dt = 1  # time interval 1 second
df["SOC (%)"] = 100 - (df["Current"].cumsum() * dt / 3600) / (initial_battery_capacity / 1000) * 100

# SoC must be positive
filtered_df = df[df["SOC (%)"] > 0]

# Interpolation
SoC2Vol = interp1d(
    filtered_df["SOC (%)"],
    filtered_df["Voltage (V)"], 
    kind='linear',
    fill_value="extrapolate"
)

""" variables that we set at this block"""
## Should be preset

# Set the thrust level at each phase
T_percentage_takeoff_max = 0.9
T_percentage_climb_max = 0.9
T_percentage_level_max = 0.6
T_percentage_turn_max = 0.55

# Restriction setting
AOA_stall = 13                      # stall AOA (degree)
AOA_takeoff_max = 10                # maximum AOA intended to be limited at takeoff (degree)
AOA_climb_max = 8                   # intended maximum AOA at climb (degree)
AOA_turn_max = 8                    # intended maximum AOA at turn (degree)
h_flap_transition = 5               # altitude at which the aircraft transitions from flap-deployed to flap-retracted (m)
max_speed = 40                      # restricted maximum speed of aircraft (m/s)
max_load_factor = 4.0               # restricted maximum load factor (m/s)
max_climb_angle = 40                # restricted maximum climb angle (degree)

""" variables can be calculated from given parameters """
## Should not be removed
m_fuel = m_total - m_empty - m_x1                           # fuel weight(kg)
W = m_total * g                                             # total takeoff weight(N)
V_stall = math.sqrt((2*W) / (rho*S*CL_max))                 # stall speed(m/s)
V_takeoff = (math.sqrt((2*W) / (rho*S*CL_max_flap)))        # takeoff speed with maximum flap deploy(m/s)
T_max = T_max_kg * g                                        # maximum static thrust (N)
# Calculate maximum thrust at each phase (N)
T_takeoff = T_percentage_takeoff_max * T_max
T_climb = T_percentage_climb_max * T_max
T_level = T_percentage_level_max * T_max
T_turn = T_percentage_turn_max * T_max

""" Lift, Drag Coefficient Calculating Function """
## calulate lift, drag coefficient at a specific AOA using interpolation function (with no flap)
# how to use : if you want to know CL at AOA 3.12, use float(CL_func(3.12)) 
# multiply (lh-lw) / lh at CL to consider the effect from horizontal tail wing
# interpolate CD using quadratic function 
# alpha_func : function to calculate AOA from given CL value
CL_func = interp1d(alpha_result, (lh-lw) / lh * np.array(CL_result), kind = 'linear', bounds_error = False, fill_value = 'extrapolate')
CD_func = interp1d(alpha_result, CD_result, kind = 'quadratic', bounds_error = False, fill_value = 'extrapolate')
alpha_func = interp1d((lh-lw) / lh * np.array(CL_result), alpha_result, kind='linear',bounds_error=False, fill_value='extrapolate') 

### Helper Functions ###

def magnitude(vector):
    # Function that calculates the magnitude of a vector
    return math.sqrt(sum(x*x for x in vector))

def calculate_level_alpha(v,T):
    #  Function that calculates the AOA required for level flight using the velocity vector and thrust
    speed = magnitude(v)
    def equation(alpha):
        CL = float(CL_func(alpha))
        L = 0.5 * rho * speed**2 * S * CL
        return L + T * math.sin(math.radians(alpha)) - W
    alpha_solution = fsolve(equation, 5, xtol=1e-8, maxfev=1000)
    return alpha_solution[0]

def battery(T, battery_capacity, dt):
    """
    T:                두 모터의 총 추력(N), 배터리 하나의 전기용량으로 계산하기 때문에 power 계산식에서 /2
    battery_capacity: 현재 남아있는 배터리 용량(mAh)
    dt:               시간 간격(초)

    SoC vs Voltage 정보는 노션 Sizing/추친 참고
    power 계산식 정확한 식으로 수정 필요하다.
    """
    SoC = battery_capacity / initial_battery_capacity * 100 # %
    battery_voltage_one_cell = SoC2Vol(SoC)
    battery_voltage = battery_voltage_one_cell * 6
    power = (T / 2) ** 1.5 / propulsion_efficiency # Calculate power required (simplified model: P = T^(3/2) / eta) (Watt)
    current_draw = (power / battery_voltage) * 1000.0 # Calculate current draw (I = P / V) in Amps, convert to mA
    battery_capacity -= (current_draw / 3600.0) * dt # Convert mA to mAh/s, calculate battery_capacity
    return battery_capacity, battery_voltage, current_draw

### Result Lists ###
time_list = []
load_factor_list = []
AOA_list = []
position_list = []
v_list = []
a_list = []
phase_index = []
bank_angle_list = []
climb_pitch_angle_list = []
T_percentage_list = []
altitude_list = []
battery_capacity_list = []
battery_voltage_list = []
battery_draw_list = []

### Acceleration Functions ###
def calculate_acceleration_groundroll(v):
    # Function that calculates the acceleration of an aircraft during ground roll
    speed = magnitude(v)
    D = 0.5 * rho * speed**2 * S * CD_zero_flap
    L = 0.5 * rho * speed**2 * S * CL_zero_flap
    a_x = (T_takeoff - D - 0.03*(W-L)) / m_total              # calculate x direction acceleration 
    return np.array([a_x, 0, 0])

def calculate_acceleration_groundrotation(v):
    # Function that calculate the acceleration of the aircraft during rotation for takeoff
    speed = magnitude(v)
    D = 0.5 * rho * speed**2 * S * CD_max_flap
    L = 0.5 * rho * speed**2 * S * CL_max_flap
    a_x = (T_takeoff - D - 0.03*(W-L)) / m_total            # calculate x direction acceleration 
    return np.array([a_x, 0, 0])

def calculate_acceleration_level(v, alpha, T):
    # Function that calculates the acceleration during level flight
    speed = magnitude(v)
    CD = float(CD_func(alpha))
    D = 0.5 * rho * speed**2 * S * CD
    a_x = (T * math.cos(math.radians(alpha)) - D) / m_total
    return np.array([a_x, 0, 0])

def calculate_acceleration_climb(v, alpha_deg, gamma_rad, z_pos):
    # Function that calculates the acceleration during climb
    speed = magnitude(v)
    if (z_pos > h_flap_transition):
        CL = float(CL_func(alpha_deg))
        CD = float(CD_func(alpha_deg))
    else:
        CL = CL_max_flap
        CD = CD_max_flap
    theta_deg = math.degrees(gamma_rad) + alpha_deg
    
    D = 0.5 * rho * speed**2 * S * CD
    L = 0.5 * rho * speed**2 * S * CL
    a_x = (T_climb * math.cos(math.radians(theta_deg)) - L * math.sin(gamma_rad) - D * math.cos(gamma_rad)) / m_total
    a_z = (T_climb * math.sin(math.radians(theta_deg)) + L * math.cos(gamma_rad) - D * math.sin(gamma_rad) - W) / m_total
    return np.array([a_x, 0, a_z])

### Simulation Functions ###

def takeoff_simulation():
    print("\nRunning Takeoff Simulation...")
    
    dt = 0.01
    v = np.array([0.0, 0.0, 0.0])
    position = np.array([0.0, 0.0, 0.0])
    t = 0.0
    battery_capacity = initial_battery_capacity
    
    # Ground roll until 0.9 times takeoff speed
    while magnitude(v) < 0.9 * V_takeoff:
        t += dt
        time_list.append(t)
        
        a = calculate_acceleration_groundroll(v)
        v -= a * dt
        position += v * dt
        
        L = 0.5 * rho * magnitude(v)**2 * S * CL_zero_flap
        battery_capacity, battery_voltage, current_draw = battery(T_takeoff, battery_capacity, dt)
        
        # Store results
        load_factor_list.append(L/W)
        v_list.append(v.copy())
        AOA_list.append(0)
        a_list.append(a)
        position_list.append(tuple(position))
        bank_angle_list.append(0)
        T_percentage_list.append(T_percentage_takeoff_max)
        climb_pitch_angle_list.append(np.nan)
        altitude_list.append(0)
        battery_draw_list.append(current_draw)
        battery_capacity_list.append(battery_capacity)
        battery_voltage_list.append(battery_voltage)
        
    # Ground rotation until takeoff speed    
    while 0.9 * V_takeoff <= magnitude(v) <= V_takeoff:
        t += dt
        time_list.append(t)
        
        a = calculate_acceleration_groundrotation(v)
        v -= a * dt
        position += v * dt
        
        L = 0.5 * rho * magnitude(v)**2 * S * CL_max_flap
        battery_capacity, battery_voltage, current_draw = battery(T_takeoff, battery_capacity, dt)
        
        # Store results
        load_factor_list.append(L/W)
        v_list.append(v.copy())
        AOA_list.append(AOA_takeoff_max)
        a_list.append(a)
        position_list.append(tuple(position))
        bank_angle_list.append(0)
        T_percentage_list.append(T_percentage_takeoff_max)
        climb_pitch_angle_list.append(np.nan)
        altitude_list.append(0)
        battery_draw_list.append(current_draw)
        battery_capacity_list.append(battery_capacity)
        battery_voltage_list.append(battery_voltage)
        
def climb_simulation(h_target, x_max_distance, direction):
    """
    Args:
        h_target (float): Desired altitude to climb at the maximum climb AOA (m)
        x_max_distance (float): Restricted x-coordinate for climb (m)
        direction (string): The direction of movement. Must be either 'left' or 'right'.
    """    
    print("\nRunning Climb Simulation...")

    if position_list[-1][2] > h_target: return
    
    dt = 0.01
    n_steps = int(60 / dt)  # Max 60 seconds simulation
    v = v_list[-1].copy()
    t = time_list[-1]
    x_pos, y_pos, z_pos = position_list[-1]
    alpha_w_deg = 0
    break_flag = 0
    battery_capacity = battery_capacity_list[-1]
    
    for step in range(n_steps):
        t += dt
        time_list.append(t)
        
        # Calculate climb angle
        gamma_rad = math.atan2(v[2], abs(v[0]))
        
        if direction == 'right':
            # set AOA at climb (if altitude is below target altitude, set AOA to AOA_climb. if altitude exceed target altitude, decrease AOA gradually to -2 degree)
            if(z_pos < h_flap_transition and x_pos < x_max_distance):
                alpha_w_deg = AOA_takeoff_max
            elif(h_flap_transition <= z_pos < h_target and x_pos < x_max_distance):
                if 0.5 * rho * magnitude(v)**2 * S * float(CL_func(AOA_climb_max)) < W * max_load_factor and gamma_rad < math.radians(max_climb_angle):
                    alpha_w_deg = AOA_climb_max
                elif 0.5 * rho * magnitude(v)**2 * S * float(CL_func(AOA_climb_max)) >= W * max_load_factor and gamma_rad < math.radians(max_climb_angle):
                    alpha_w_deg = float(alpha_func((2 * W * max_load_factor)/(rho * magnitude(v)**2 * S)))
                else:
                    alpha_w_deg -= 1
                    alpha_w_deg = max(alpha_w_deg, -5) 
            else:
                break_flag = 1
                if gamma_rad > math.radians(max_climb_angle):
                    alpha_w_deg -= 1
                    alpha_w_deg = max(alpha_w_deg, -5)
                else:
                    alpha_w_deg -= 0.1
                    alpha_w_deg = max(alpha_w_deg , -5)         
        
        if direction == 'left':
            # set AOA at climb (if altitude is below target altitude, set AOA to AOA_climb. if altitude exceed target altitude, decrease AOA gradually to -2 degree)
            if(z_pos < h_flap_transition and x_pos > x_max_distance):
                alpha_w_deg = AOA_takeoff_max
            elif(h_flap_transition <= z_pos < h_target and x_pos > x_max_distance):

                if 0.5 * rho * magnitude(v)**2 * S * float(CL_func(AOA_climb_max)) < W * max_load_factor and gamma_rad < math.radians(max_climb_angle):
                    alpha_w_deg = AOA_climb_max
                elif 0.5 * rho * magnitude(v)**2 * S * float(CL_func(AOA_climb_max)) >= W * max_load_factor and gamma_rad < math.radians(max_climb_angle):
                    alpha_w_deg = float(alpha_func((2 * W * max_load_factor)/(rho * magnitude(v)**2 * S)))
                else:
                    alpha_w_deg -= 1
                    alpha_w_deg = max(alpha_w_deg, -5) 
            else:
                break_flag = 1
                if gamma_rad > math.radians(max_climb_angle):
                    alpha_w_deg -= 1
                    alpha_w_deg = max(alpha_w_deg, -5)
                else:
                    alpha_w_deg -= 0.1
                    alpha_w_deg = max(alpha_w_deg , -5)   
                
        # Calculate load factor
        if (z_pos < h_flap_transition):
            CL = CL_max_flap
        else:
            CL = float(CL_func(alpha_w_deg))
        L = 0.5 * rho * magnitude(v)**2 * S * CL
        load_factor = L / W
        load_factor_list.append(load_factor)

        # RK4 integration
        a1 = calculate_acceleration_climb(v, alpha_w_deg, gamma_rad, z_pos)
        v1 = v + (a1*dt/2)
        a2 = calculate_acceleration_climb(v1, alpha_w_deg, gamma_rad, z_pos)
        v2 = v + (a2*dt/2)
        a3 = calculate_acceleration_climb(v2, alpha_w_deg, gamma_rad,z_pos)
        v3 = v + a3*dt
        a4 = calculate_acceleration_climb(v3, alpha_w_deg, gamma_rad, z_pos)
        
        a = (a1 + 2*a2 + 2*a3 + a4)/6
        
        if direction == 'right':
            v[0] += a[0]*dt
            v[2] += a[2]*dt
        else:
            v[0] -= a[0]*dt
            v[2] += a[2]*dt
        
        # Update position
        x_pos += v[0] * dt
        z_pos += v[2] * dt
        position_list.append((x_pos, y_pos, z_pos))
        
        battery_capacity, battery_voltage, current_draw = battery(T_climb, battery_capacity, dt)

        # Store results
        v_list.append(v.copy())
        AOA_list.append(alpha_w_deg)
        a_list.append(a)
        bank_angle_list.append(math.degrees(0))
        T_percentage_list.append(T_percentage_climb_max)
        climb_pitch_angle_list.append(alpha_w_deg + math.degrees(gamma_rad))
        altitude_list.append(z_pos)
        battery_draw_list.append(current_draw)
        battery_capacity_list.append(battery_capacity)
        battery_voltage_list.append(battery_voltage)

        # break when climb angle goes to zero
        if break_flag == 1 and gamma_rad < 0:
            print(f"cruise altitude is {z_pos:.2f} m.")
            break

def level_flight_simulation(x_final, direction):
    """
    Args:
        x_final (float): Restricted x-coordinate for level flight (m)
        direction (string): The direction of movement. Must be either 'left' or 'right'.
    """        
    print("\nRunning Cruise Simulation...")
    
    dt = 0.1
    max_steps = int(180/dt) # max 3 minuites
    step = 0
    
    # Initialize vectors
    v = v_list[-1].copy()
    v[2] = 0  # Zero vertical velocity
    speed = magnitude(v)
    if direction == 'right':
        v = np.array([speed, 0, 0])  # Align with x-axis
    else:
        v = np.array([-speed, 0, 0])
        
    t = time_list[-1]
    x_pos, y_pos, z_pos = position_list[-1]
    battery_capacity = battery_capacity_list[-1]
    cruise_flag = 0
    
    while step < max_steps:
        step += 1
        t += dt
        time_list.append(t)
        
        # Calculate alpha_w first
        alpha_w_deg = calculate_level_alpha(v, T_level)
            
        # Speed limiting while maintaining direction
        speed = magnitude(v)
        if speed > max_speed:  # Original speed limit
            cruise_flag = 1

        if cruise_flag == 1:
            v = v * (max_speed / speed)
            T_cruise = 0.5 * rho * max_speed**2 * S * float(CD_func(alpha_w_deg))
            alpha_w_deg = calculate_level_alpha(v, T_cruise)
            T_percentage_list.append(T_cruise / T_max)
            battery_capacity, battery_voltage, current_draw = battery(T_cruise, battery_capacity, dt)

            # RK4 integration
            a1 = calculate_acceleration_level(v, alpha_w_deg, T_cruise)
            v1 = v + a1 * dt / 2
            a2 = calculate_acceleration_level(v1, alpha_w_deg, T_cruise)
            v2 = v + a2 * dt / 2
            a3 = calculate_acceleration_level(v2, alpha_w_deg, T_cruise)
            v3 = v + a3 * dt
            a4 = calculate_acceleration_level(v3, alpha_w_deg, T_cruise)
        else:
            T_percentage_list.append(T_percentage_level_max)
            battery_capacity, battery_voltage, current_draw = battery(T_level, battery_capacity, dt)

            # RK4 integration
            a1 = calculate_acceleration_level(v, alpha_w_deg, T_level)
            v1 = v + a1 * dt / 2
            a2 = calculate_acceleration_level(v1, alpha_w_deg, T_level)
            v2 = v + a2 * dt / 2
            a3 = calculate_acceleration_level(v2, alpha_w_deg, T_level)
            v3 = v + a3 * dt
            a4 = calculate_acceleration_level(v3, alpha_w_deg, T_level)
            
        # Update Acc, Vel, position
        a = (a1 + 2 * a2 + 2 * a3 + a4) / 6
        if direction == 'right': v += a * dt
        else: v -= a * dt
        dx = v[0] * dt
        dy = v[1] * dt
        x_pos += dx
        y_pos += dy
        position_list.append((x_pos, y_pos, z_pos))
        
        # Calculate and store results
        L = 0.5 * rho * speed**2 * S * float(CL_func(alpha_w_deg))
        
        # Store results
        load_factor_list.append(L / W)
        v_list.append(v.copy())
        AOA_list.append(alpha_w_deg)
        a_list.append(a)
        bank_angle_list.append(math.degrees(0))
        climb_pitch_angle_list.append(np.nan)
        altitude_list.append(z_pos)
        battery_draw_list.append(current_draw)
        battery_capacity_list.append(battery_capacity)
        battery_voltage_list.append(battery_voltage)
        
        # Check if we've reached target x position
        if direction == 'right':
            if x_pos >= x_final:
                break
        else:
            if x_pos <= x_final:
                break

def turn_simulation(target_angle_deg, direction):
    """
    Args:
        target_angle_degree (float): Required angle of coordinate level turn (degree)
        direction (string): The direction of movement. Must be either 'CW' or 'CCW'.
    """     
    print("\nRunning Turn Simulation...")
    
    # 초기 설정
    dt = 0.01
    v = v_list[-1].copy()
    t = time_list[-1]
    x_pos, y_pos, z_pos = position_list[-1]
    speed = magnitude(v)
    battery_capacity = battery_capacity_list[-1]

    # Initialize turn tracking
    target_angle_rad = math.radians(target_angle_deg)
    turned_angle_rad = 0

    # Get initial heading and setup turn center
    initial_angle_rad = math.atan2(v[1], v[0])
    current_angle_rad = initial_angle_rad

    # Turn
    while abs(turned_angle_rad) < abs(target_angle_rad):
        t += dt
        time_list.append(t)
        
        if speed < max_speed:
            CL = min(float(CL_func(AOA_turn_max)), (2*max_load_factor*W)/(rho * speed**2 * S))
            alpha_turn = float(alpha_func(CL)) 
            L = CL * (0.5 * rho * speed**2) * S
            phi_rad = math.acos(W/L)
            a_centripetal = (L * math.sin(phi_rad)) / m_total
            R = (m_total * speed**2)/(L * math.sin(phi_rad))
            omega = speed / R
            load_factor = 1 / math.cos(phi_rad)

            CD = float(CD_func(alpha_turn))
            D = CD * (0.5 * rho * speed**2) * S
            a_tangential = (T_turn - D) / m_total
            T_percentage_list.append(T_percentage_turn_max) 
            speed += a_tangential * dt
            battery_capacity, battery_voltage, current_draw = battery(T_turn, battery_capacity, dt)
        
        elif speed >= max_speed : 
            speed = max_speed
            CL = min(float(CL_func(AOA_turn_max)), (2*max_load_factor*W)/(rho * speed**2 * S))
            alpha_turn = float(alpha_func(CL)) 
            L = CL * (0.5 * rho * speed**2) * S
            phi_rad = math.acos(W/L)
            a_centripetal = (L * math.sin(phi_rad)) / m_total
            R = (m_total * speed**2)/(L * math.sin(phi_rad))
            omega = speed / R
            load_factor = 1 / math.cos(phi_rad)

            CD = float(CD_func(alpha_turn))
            D = CD * (0.5 * rho * speed**2) * S
            T = min(D, T_turn)
            T_percentage_list.append(T/T_max)
            a_tangential = (T - D) / m_total
            speed += a_tangential * dt
            battery_capacity, battery_voltage, current_draw = battery(T, battery_capacity, dt)

        # Calculate turn center
        if direction == "CCW":
            center_x = x_pos - R * math.sin(current_angle_rad)
            center_y = y_pos + R * math.cos(current_angle_rad)
        else:
            center_x = x_pos + R * math.sin(current_angle_rad)
            center_y = y_pos - R * math.cos(current_angle_rad)

        # Update heading based on angular velocity
        if direction == "CCW":
            current_angle_rad += omega * dt
            turned_angle_rad += omega * dt
        else:
            current_angle_rad -= omega * dt
            turned_angle_rad -= omega * dt
        
        # Calculate new position relative to turn center
        if direction == "CCW":
            x_pos = center_x + R * math.sin(current_angle_rad)
            y_pos = center_y - R * math.cos(current_angle_rad)
        else:
            x_pos = center_x - R * math.sin(current_angle_rad)
            y_pos = center_y + R * math.cos(current_angle_rad)

        # Update velocity direction (tangent to the circular path)
        v = np.array([
            speed * math.cos(current_angle_rad),
            speed * math.sin(current_angle_rad),
            0
        ])

        a = np.array([a_tangential * math.cos(current_angle_rad) - a_centripetal * math.sin(current_angle_rad),
                     a_tangential * math.sin(current_angle_rad) + a_centripetal * math.cos(current_angle_rad),
                     0])
        
        # Store results
        a_list.append(a)
        position_list.append((x_pos, y_pos, z_pos))
        v_list.append(v.copy())
        load_factor_list.append(load_factor)
        AOA_list.append(alpha_turn)
        bank_angle_list.append(math.degrees(phi_rad))
        climb_pitch_angle_list.append(np.nan)
        altitude_list.append(z_pos)
        battery_draw_list.append(current_draw)
        battery_capacity_list.append(battery_capacity)
        battery_voltage_list.append(battery_voltage)
        
### Mission Function & Plotting ###
def run_mission2():
    phase_index.append(0)

    ### Lap 1 ###
    # Phase 1: Takeoff
    takeoff_simulation()
    print(f"Takeoff Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 2: Climb to 25m
    climb_simulation(25, -140, direction="left")
    print(f"Climb Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 3: Level flight
    level_flight_simulation(-152, direction="left")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 4: Half turn (180 degrees)
    turn_simulation(180, direction="CW")
    print(f"Half Turn Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
 
    # Phase 5: Climb if it is not above 25m
    climb_simulation(25, -10, direction="right")
    print(f"Climb Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
        
    # Phase 6: Level flight
    level_flight_simulation(0, direction="right")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 7: Full loop (360 degrees)
    turn_simulation(360, direction="CCW")
    print(f"Loop Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 8: Level flight
    level_flight_simulation(152, direction="right")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 9: Half turn (180 degrees)
    turn_simulation(180, direction="CW")
    print(f"Half Turn Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 10: Level flight
    level_flight_simulation(-152, direction="left")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    ### Lap 2 ###
    # Phase 11: Half turn (180 degrees)
    turn_simulation(180, direction="CW")
    print(f"Half Turn Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))   
    
    # Phase 12: Level flight
    level_flight_simulation(0, direction="right")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))   
    
    # Phase 13: Full loop
    turn_simulation(360, direction="CCW")
    print(f"Loop Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))
    
    # Phase 14: Level flight
    level_flight_simulation(152, direction="right")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))      
    
    # Phase 15: Half turn
    turn_simulation(180, direction="CW")
    print(f"Half Turn Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))     
    
    # Phase 16: Level flight
    level_flight_simulation(-152, direction="left")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))    

    ### Lap 3 ###
    # Phase 17: Half turn
    turn_simulation(180, direction="CW")
    print(f"Half Turn Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))  
    
    # Phase 18: Level flight
    level_flight_simulation(0, direction="right")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))      
    
    # Phase 19: Full loop
    turn_simulation(360, direction="CCW")
    print(f"Loop Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list)) 
    
    # Phase 20: Level flight
    level_flight_simulation(152, direction="right")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))  
    
    # Phase 21: Half turn
    turn_simulation(180, direction="CW")
    print(f"Half Turn Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))      

    # Phase 22: Level flight
    level_flight_simulation(0, direction="left")
    print(f"Level Flight Complete at position: {position_list[-1]}")
    phase_index.append(len(time_list))

    # Calulate Objective2 (fuel wight / flight time)
    obj2 = m_fuel / time_list[-1]
    print(f"\nObjective2 : {obj2}")
    
def plot_results():
    x_coords = [pos[0] for pos in position_list]
    y_coords = [pos[1] for pos in position_list]
    z_coords = [pos[2] for pos in position_list]
    speeds = [magnitude(v) for v in v_list]
    
    plt.figure(figsize=(20, 10))

    gridspec = plt.GridSpec(3, 3, width_ratios=[1, 1, 1], height_ratios=[1, 1, 1])

    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'orange', 'purple']  # Define colors for phases

    # 3D trajectory
    ax1 = plt.subplot(gridspec[0:2, 0], projection='3d')
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax1.plot(x_coords[start:end], y_coords[start:end], z_coords[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")

    # Get current axis limits
    x_limits = ax1.get_xlim()
    y_limits = ax1.get_ylim()
    z_limits = ax1.get_zlim()

    # Find the max range for uniform scaling
    x_range = x_limits[1] - x_limits[0]
    y_range = y_limits[1] - y_limits[0]
    z_range = z_limits[1] - z_limits[0]
    max_range = max(x_range, y_range, z_range)

    # Set the new limits
    mid_x = 0.5 * (x_limits[0] + x_limits[1])
    mid_y = 0.5 * (y_limits[0] + y_limits[1])
    mid_z = 0.5 * (z_limits[0] + z_limits[1])
    ax1.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
    ax1.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
    ax1.set_zlim(mid_z - max_range / 2, mid_z + max_range / 2)

    ax1.set_title('3D Flight Path')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Z (m)')

    # Speed profile
    ax2 = plt.subplot(gridspec[0, 1])
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax2.plot(time_list[start:end], speeds[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")
    ax2.set_title('Speed vs Time')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Speed (m/s)')
    ax2.grid(True)

    # AOA profile
    ax3 = plt.subplot(gridspec[1, 1])
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax3.plot(time_list[start:end], AOA_list[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")
    ax3.set_title('AOA vs Time')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('AOA (deg)')
    ax3.grid(True)

    # Bank angle profile
    ax4 = plt.subplot(gridspec[2, 1])
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax4.plot(time_list[start:end], bank_angle_list[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")
    ax4.set_title('Bank Angle vs Time')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Bank Angle (deg)')
    ax4.grid(True)

    # Load Factor profile
    ax5 = plt.subplot(gridspec[0, 2])
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax5.plot(time_list[start:end], load_factor_list[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")
    ax5.set_title('Load Factor vs Time')
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Load Factor')
    ax5.grid(True)

    # Thrust Percentage profile
    ax6 = plt.subplot(gridspec[1, 2])
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax6.plot(time_list[start:end], T_percentage_list[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")
    ax6.set_title('Thrust Percentage vs Time')
    ax6.set_xlabel('Time (s)')
    ax6.set_ylabel('Thrust Percentage')
    ax6.grid(True)

    # Climb Pitch Angle profile
    ax7 = plt.subplot(gridspec[2, 2])
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax7.plot(time_list[start:end], climb_pitch_angle_list[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")
    ax7.set_title('Climb Pitch Angle vs Time')
    ax7.set_xlabel('Time (s)')
    ax7.set_ylabel('Pitch Angle (deg)')
    ax7.grid(True)
    
    # Battery voltage profile
    ax8 = plt.subplot(gridspec[2, 0])
    for i in range(len(phase_index) - 1):
        start, end = phase_index[i], phase_index[i + 1]
        ax8.plot(time_list[start:end], battery_voltage_list[start:end], color=colors[i % len(colors)], label=f"Phase {i+1}")
    ax8.set_title('Battery Voltage vs Time')
    ax8.set_xlabel('Time (s)')
    ax8.set_ylabel('Battery Voltage (V)')
    ax8.grid(True)    

    plt.tight_layout()
    plt.show()   
    
def save_results():
    import os

    # Create a result directory if it does not exist
    results = "results"
    if not os.path.exists(results):
        os.makedirs(results)

    # Save data to a .npz file
    np.savez(
        os.path.join(results, "mission2.npz"), 
        time_list=time_list, 
        load_factor_list=load_factor_list, 
        AOA_list=AOA_list, 
        position_list=position_list, 
        v_list=v_list, 
        a_list=a_list, 
        phase_index=phase_index,
        bank_angle_list=bank_angle_list
    )

    print(f"\nData saved to {os.path.join(results, 'mission2.npz')}\n")

if __name__ == "__main__":
    run_mission2()
    plot_results()
    # save_results()
