# Synthetic Trip Simulator Data Dictionary

This document describes the generated columns in the simulator output.

Legend:
- `latent` means internal state used by the simulator and generally not suitable as an ML input if you want a realistic deployment setup.
- `observed` means noisy or directly observable at prediction time.
- `debug` means useful for validation, not recommended for model training.

## Identity and entity columns

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `trip_id` | Unique trip identifier | id | debug | no | traceability |
| `driver_id` | Persistent driver identifier | id | observed | usually no | grouping, repeated behavior |
| `vehicle_id` | Persistent vehicle identifier | id | observed | usually no | vehicle reuse |
| `driver_vehicle_pair_id` | Persistent driver-vehicle pairing key | id | debug | no | reuse audit |
| `driver_trip_index` | Trip index within a driver | count | debug | no | repeated-trip analysis |

## Driver latent profile columns

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `aggressiveness` | Tendency toward hard acceleration and braking | [0,1] | latent | no by default | speed, stop-go, harsh braking |
| `consistency` | Behavioral consistency across trips | [0,1] | latent | no by default | variance, speed noise |
| `eco_awareness` | Preference for efficient driving | [0,1] | latent | no by default | mode choice, efficiency |
| `range_anxiety` | Concern about remaining battery range | [0,1] | latent | no by default | mode choice, SOC reserve |
| `hvac_preference` | Willingness to use heating/cooling aggressively | [0,1] | latent | no by default | HVAC load |
| `speeding_tendency` | Desire to drive above baseline speeds | [0,1] | latent | no by default | avg speed, duration |
| `braking_smoothness` | Smoothness of braking and deceleration | [0,1] | latent | no by default | stop-go penalties, regen |
| `charging_discipline` | Tendency to keep battery charge healthy | [0,1] | latent | no by default | SOC evolution |
| `route_familiarity_bias` | Preference for familiar routes | [0,1] | latent | no by default | detours, stop-go |
| `schedule_pressure` | Time pressure on the trip | [0,1] | latent | no by default | speed, harsh braking, traffic sensitivity |
| `traffic_uncertainty` | Driver sensitivity to traffic ambiguity | [0,1] | latent | no by default | detours, variance |
| `vehicle_health_factor` | Driver-side care factor for the vehicle | [0,1] | latent | no by default | wear-related efficiency |
| `battery_health` | Driver-side battery care proxy | [0,1] | latent | no by default | EV efficiency, SOC decay |
| `tire_condition` | Tire maintenance proxy | [0,1] | latent | no by default | rolling resistance |
| `preferred_trip_purposes` | Common trip purposes for this driver | list | latent | no by default | purpose sampling |

## Vehicle profile columns

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `archetype` | Vehicle archetype label | categorical | observed | yes | broad vehicle behavior |
| `make` | Vehicle make | categorical | observed | optional | vehicle grouping |
| `model` | Vehicle model | categorical | observed | optional | vehicle grouping |
| `powertrain_type` | EV, hybrid, or ICE | categorical | observed | yes | energy model, label policy |
| `body_type` | Hatchback, sedan, SUV | categorical | observed | yes | mass/drag expectations |
| `battery_capacity_kwh` | Nominal battery capacity | kWh | observed | yes | EV/hybrid SOC, battery risk |
| `usable_battery_kwh` | Usable battery capacity | kWh | observed | yes | SOC depletion, range risk |
| `fuel_tank_l` | Fuel tank capacity | liters | observed | yes | range context |
| `mass_kg` | Curb mass | kg | observed | yes | energy, acceleration losses |
| `drag_coeff` | Aerodynamic drag coefficient | unitless | observed | yes | highway energy use |
| `frontal_area_m2` | Vehicle frontal area | m^2 | observed | yes | aero drag |
| `rolling_resistance_coeff` | Rolling resistance coefficient | unitless | observed | yes | city/highway energy use |
| `drivetrain_efficiency` | Drivetrain efficiency proxy | unitless | observed | yes | energy conversion |
| `regen_efficiency` | Regenerative braking efficiency | unitless | observed | yes | EV/hybrid recovery |
| `hvac_base_kw` | Base HVAC load | kW | observed | yes | HVAC energy |
| `city_efficiency_factor` | City operation efficiency multiplier | unitless | observed | yes | urban energy use |
| `highway_efficiency_factor` | Highway operation efficiency multiplier | unitless | observed | yes | highway energy use |
| `nominal_ev_range_km` | Approximate EV range | km | observed | yes | battery risk, mode choice |
| `battery_health` | Battery health proxy | [0,1] | observed | yes | EV efficiency degradation |
| `vehicle_health_factor` | Overall vehicle health proxy | [0,1] | observed | yes | rolling resistance, wear |

## Trip context columns

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `city` | City of the trip | categorical | observed | yes | weather, traffic, emissions |
| `season` | Season of the trip | categorical | observed | yes | weather, temperature |
| `weather` | Sampled weather state | categorical | observed | yes | speed, HVAC, safety |
| `ambient_temp_c` | Ambient temperature | Celsius | observed | yes | HVAC, battery efficiency |
| `humidity` | Relative humidity | ratio | observed | yes | HVAC, weather discomfort |
| `wind_speed_kmh` | Wind speed | km/h | observed | yes | aero drag, weather penalty |
| `precipitation_mm` | Precipitation intensity | mm | observed | yes | traffic, speed, weather penalty |
| `departure_hour` | Hour of departure | hour | observed | yes | congestion, purpose pattern |
| `day_type` | Weekday or weekend | categorical | observed | yes | purpose and traffic patterns |
| `trip_purpose` | Purpose of the trip | categorical | observed | yes | distance, cargo, urgency |
| `road_type` | Road class mix for the trip | categorical | observed | yes | speed, stop-go, energy use |
| `traffic_level` | Congestion intensity | [0,1] | observed | yes | duration, speed variance |
| `expected_congestion` | Expected congestion proxy | [0,1] | observed | yes | mode choice, duration |
| `base_distance_km` | Planned distance before behavior adjustment | km | observed | yes | all targets |
| `distance_km` | Actual simulated trip distance after detour factor | km | debug/target-side | usually no | baseline physics |
| `elevation_gain_m` | Total ascent | m | observed | yes | duration, energy use |
| `elevation_loss_m` | Total descent | m | observed | yes | energy use, regen |
| `passengers` | Passenger count | count | observed | yes | mass and energy load |
| `cargo_kg` | Cargo mass | kg | observed | yes | mass and energy load |

## Behavior columns

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `behavior_speed_factor` | Speed multiplier from behavior | unitless | latent | no by default | avg speed, duration |
| `behavior_stop_go_multiplier` | Stop-and-go multiplier | unitless | latent | no by default | stop count, duration |
| `behavior_hvac_multiplier` | HVAC usage multiplier | unitless | latent | no by default | HVAC energy |
| `behavior_regen_multiplier` | Regen usage multiplier | unitless | latent | no by default | battery use |
| `behavior_route_detour_factor` | Route inefficiency multiplier | unitless | latent | no by default | distance, energy |
| `behavior_battery_reserve_soc` | Reserve SOC target | [0,1] | latent | no by default | SOC floor, battery risk |
| `behavior_speed_variability` | Speed variability multiplier | unitless | latent | no by default | speed noise, duration variance |
| `behavior_harsh_braking_probability` | Probability of harsh braking | [0,1] | latent | no by default | stop penalties, regen |

## True physics outputs

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `true_duration_min` | Physically simulated duration | minutes | debug/target-side | no | time target generation |
| `true_avg_speed_kmh` | Actual average speed | km/h | debug | no | duration, energy |
| `true_battery_used_kwh` | Actual battery energy used | kWh | debug/target-side | no | battery target generation |
| `true_fuel_used_l` | Actual fuel used | liters | debug/target-side | no | cost/emissions |
| `true_energy_cost` | True trip energy cost | currency units | debug | no | cost target generation |
| `true_emissions` | True emissions estimate | kg CO2e | debug | no | mode policy |
| `true_stop_count` | Simulated stop count | count | debug | no | duration, energy |
| `true_hvac_kw` | HVAC load used in physics | kW | debug | no | energy model |
| `true_total_energy_kwh` | Combined propulsion + HVAC energy | kWh | debug | no | diagnostics |
| `true_propulsion_energy_kwh` | Non-HVAC propulsion energy | kWh | debug | no | diagnostics |
| `mass_kg_effective` | Effective loaded mass | kg | debug | no | physics validation |

## Battery state columns

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `true_battery_soc_start_pct` | True SOC at trip start | percent | debug | no | battery target, diagnostics |
| `true_battery_soc_end_pct` | True SOC at trip end | percent | debug | no | battery target, diagnostics |
| `battery_soc_start` | Normalized start SOC | ratio | debug | no | diagnostics |
| `battery_soc_end` | Normalized end SOC | ratio | debug | no | diagnostics |

## Mode policy outputs

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `mode_score_ev` | Policy score for EV | score | debug | no | label selection |
| `mode_score_hybrid` | Policy score for hybrid | score | debug | no | label selection |
| `mode_score_ice` | Policy score for ICE | score | debug | no | label selection |
| `mode_prob_ev` | Softmax probability for EV | probability | debug | no | label uncertainty |
| `mode_prob_hybrid` | Softmax probability for hybrid | probability | debug | no | label uncertainty |
| `mode_prob_ice` | Softmax probability for ICE | probability | debug | no | label uncertainty |
| `recommended_mode` | Final probabilistic mode label | categorical | target | yes | classification target |
| `recommended_mode_score_margin` | Margin between top two scores | score | debug | no | uncertainty audit |
| `switch_point_km` | Hybrid switch threshold estimate | km | target | yes | switch-point regression target |

## Regression targets

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `estimated_cost` | Noisy estimated trip cost | currency units | target | yes | cost regression |
| `estimated_time_min` | Noisy estimated trip duration | minutes | target | yes | time regression |
| `battery_used_kwh` | Noisy estimated battery use | kWh | target | yes | battery regression |

## Observed sensor columns

| Column | Meaning | Units | Type | ML use | Influences |
| --- | --- | --- | --- | --- | --- |
| `observed_distance_km` | Noisy measured distance | km | observed | optional | validation |
| `observed_avg_speed_kmh` | Noisy measured average speed | km/h | observed | optional | validation |
| `measured_ambient_temp_c` | Noisy measured ambient temperature | Celsius | observed | optional | validation |
| `observed_soc_pct` | Noisy SOC reading | percent | observed | optional | validation |
| `observed_soc_start_pct` | Noisy SOC at start | percent | observed | optional | validation |
| `observed_soc_end_pct` | Noisy SOC at end | percent | observed | optional | validation |
| `observed_traffic_level` | Noisy traffic estimate | [0,1] | observed | optional | validation |
| `estimated_true_duration_min_sensor` | Noisy duration sensor estimate | minutes | observed | optional | validation |
| `estimated_true_battery_used_kwh_sensor` | Noisy battery sensor estimate | kWh | observed | optional | validation |
| `estimated_true_fuel_used_l_sensor` | Noisy fuel sensor estimate | liters | observed | optional | validation |
| `observed_elevation_gain_m` | Noisy elevation gain estimate | m | observed | optional | validation |
| `observed_elevation_loss_m` | Noisy elevation loss estimate | m | observed | optional | validation |

## Recommended ML usage

- Use `recommended_mode`, `estimated_cost`, `estimated_time_min`, `battery_used_kwh`, and `switch_point_km` as the primary targets.
- Use `observed` context and vehicle columns as inputs.
- Avoid `true_` columns, `mode_score_*`, `mode_prob_*`, and `recommended_mode_score_margin` for training unless you are doing explicit oracle experiments.
- Keep `driver_id` and `vehicle_id` for grouping or split logic, not as direct model inputs.
