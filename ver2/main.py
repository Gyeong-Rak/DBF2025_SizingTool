## Does all the main work

import cProfile
import pstats
import pandas as pd
from pstats import SortKey
from vsp_grid import runVSPGridAnalysis
from mission_grid import runMissionGridSearch, save_mission_results
from vsp_analysis import  loadAnalysisResults, visualize_results
from mission_analysis import MissionAnalyzer, visualize_mission
from models import *
from config import *

def main():

    presetValues = PresetValues(
        m_x1 = 0.2,                       # kg
        x1_flight_time = 30,              # sec
        max_battery_capacity = 2250,      # mAh (per one battery)
        Thrust_max = 6.6,                 # kg (two motors)
        min_battery_voltage = 20,         # V (원래는 3 x 6 = 18 V 인데 안전하게 20 V)
        propulsion_efficiency = 0.8,      # Efficiency of the propulsion system
        score_weight_ratio = 1            # mission2/3 score weight ratio
        )
    aircraftParamConstraints=            AircraftParamConstraints (
                #Constraints for constructing the aircraf

                # wing parameter ranges
                span_max = 1800.0,                   # mm
                span_min = 1800.0,
                span_interval = 100.0,
                AR_max = 5.45,
                AR_min = 5.45,
                AR_interval = 0.5,
                taper_max = 0.65,                       # (root chord) / (tip chord)
                taper_min = 0.25,
                taper_interval = 0.1,
                twist_max = 0.0,                       # degree
                twist_min = 0.0,
                twist_interval = 1.0,
                )

    
    #runVSPGridAnalysis(
    #        aircraftParamConstraints, presetValues, 
    #        Aircraft(
    #           m_total = 8500, m_fuselage = 5000,

    #           wing_density = 0.0000852, spar_density = 1.0,

    #           mainwing_span = 1800,        
    #           mainwing_AR = 5.45,           
    #           mainwing_taper = 0.65,        
    #           mainwing_twist = 0.0,        
    #           mainwing_sweepback = 0,   
    #           mainwing_dihedral = 5.0,     
    #           mainwing_incidence = 2.0,    

    #           flap_start = [0.05, 0.4],            
    #           flap_end = [0.25, 0.6],              
    #           flap_angle = [20.0, 15.0],           
    #           flap_c_ratio = [0.35, 0.35],         

    #           horizontal_volume_ratio = 0.7,
    #           horizontal_area_ratio = 0.25, 
    #           horizontal_AR = 4.0,         
    #           horizontal_taper = 1,      
    #           horizontal_ThickChord = 8,

    #           vertical_volume_ratio = 0.053,
    #           vertical_taper = 0.6,        
    #           vertical_ThickChord = 9  
    #           ))

    results = pd.read_csv("data/test.csv", sep='|', encoding='utf-8')
    print(results.head()) 
    for hashVal in results["hash"]:
        print(f"Analyzing for hash{hashVal}")
        a=loadAnalysisResults(hashVal)

        #visualize_results(a)

    
        score, param = runMissionGridSearch(hashVal,
                              MissionParamConstraints (
                                  # total mass of the aircraft
                                  m_total_max = 8000,
                                  m_total_min = 6000,
                                  m_total_interval = 5000,
                                  #Constraints for calculating missions
                                  throttle_climb_min = 1.0,
                                  throttle_climb_max = 1.0,
                                  throttle_turn_min = 0.7,
                                  throttle_turn_max = 0.7,
                                  throttle_level_min = 1.0,
                                  throttle_level_max = 1.0,
                                  throttle_analysis_interval = 0.05,
                                  ),
                              presetValues
                              )
    
        save_mission_results(hashVal,score,param)


        missionAnalyzer = MissionAnalyzer(a,param[0],presetValues) 
        missionAnalyzer.run_mission2()
        #visualize_mission(missionAnalyzer.stateLog)

        missionAnalyzer = MissionAnalyzer(a,param[1],presetValues) 
        missionAnalyzer.run_mission3()
        #visualize_mission(missionAnalyzer.stateLog)

        
    return


if __name__== "__main__":
    main()
