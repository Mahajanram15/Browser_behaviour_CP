# Machine Learning Feature Schema Specification

This document details the complete dictionary of **76 deterministic behavioral features** extracted by the feature engineering pipeline from raw, privacy-preserving browser telemetry.

---

## Summary of Feature Groups

| Group | Category | Feature Count | Primary Source Event |
| :--- | :--- | :--- | :--- |
| **A** | Mouse Movement Dynamics | 16 | `mouse_move` |
| **B** | Click Dynamics & Targets | 11 | `mouse_click` |
| **C** | Keyboard Dynamics (Metadata) | 14 | `key_meta` |
| **D** | Scroll Dynamics | 10 | `scroll` |
| **E** | Navigation & Routing | 9 | `navigation` |
| **F** | Visibility & Focus | 8 | `visibility` |
| **G** | Cross-Behavior Session Statistics | 8 | Combined Session |
| **Total** | | **76 Features** | |

---

## Group A: Mouse Movement Dynamics (16 Features)

| Feature Name | Source | Unit | Mathematical Definition | Interpretation | Missing Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `mouse_event_count` | `mouse_move` | count | Total sampled movement events | Motor activity volume | 0.0 |
| `mouse_session_duration_ms` | `mouse_move` | ms | $t_{\text{last\_move}} - t_{\text{first\_move}}$ | Active pointer time window | 0.0 |
| `mouse_total_distance_px` | `mouse_move` | px | $\sum \Delta d_i$ | Total cursor trajectory length | 0.0 |
| `mouse_mean_velocity` | `mouse_move` | px/s | $\frac{1}{N}\sum v_i$ | Average cursor speed | 0.0 |
| `mouse_std_velocity` | `mouse_move` | px/s | $\sqrt{\frac{1}{N}\sum (v_i - \bar{v})^2}$ | Velocity variability (humans show high variance) | 0.0 |
| `mouse_max_velocity` | `mouse_max` | px/s | $\max(v_i)$ | Peak pointer speed | 0.0 |
| `mouse_mean_acceleration` | `mouse_move` | px/s² | $\frac{1}{N}\sum a_i$ | Average acceleration | 0.0 |
| `mouse_std_acceleration` | `mouse_move` | px/s² | $\sigma(a_i)$ | Motor jerkiness / micro-jitter | 0.0 |
| `mouse_max_acceleration` | `mouse_move` | px/s² | $\max(a_i)$ | Peak acceleration burst | 0.0 |
| `mouse_direction_change_count` | `mouse_move` | count | $\sum \mathbb{I}(\Delta \theta_i > 5^\circ)$ | Curvature changes along trajectory | 0.0 |
| `mouse_direction_change_rate` | `mouse_move` | count/s | $\frac{\text{direction\_changes}}{\Delta t_{\text{mouse\_sec}}}$ | Frequency of angular turns | 0.0 |
| `mouse_mean_direction_change` | `mouse_move` | degrees | $\frac{1}{K}\sum \Delta \theta_k$ | Average deflection angle | 0.0 |
| `mouse_pause_count` | `mouse_move` | count | $\sum \mathbb{I}(\Delta t_i > 100\text{ms})$ | Cognitive pauses during navigation | 0.0 |
| `mouse_mean_pause_ms` | `mouse_move` | ms | $\frac{1}{P}\sum \Delta t_{\text{pause}}$ | Average hesitation duration | 0.0 |
| `mouse_max_pause_ms` | `mouse_move` | ms | $\max(\Delta t_{\text{pause}})$ | Longest cursor pause | 0.0 |
| `mouse_path_straightness` | `mouse_move` | ratio [0,1] | $\frac{\sqrt{(x_N - x_1)^2 + (y_N - y_1)^2}}{\sum \Delta d_i}$ | Trajectory efficiency (1.0 = straight line) | 0.0 (or 1.0 if stationary) |

---

## Group B: Click Dynamics (11 Features)

| Feature Name | Source | Unit | Mathematical Definition | Interpretation | Missing Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `click_count` | `mouse_click` | count | Total clicks | Interaction frequency | 0.0 |
| `click_rate` | `mouse_click` | clicks/s | $\frac{\text{click\_count}}{\Delta t_{\text{session\_sec}}}$ | Click cadence across session | 0.0 |
| `mean_click_interval_ms` | `mouse_click` | ms | $\frac{1}{C}\sum \Delta t_{\text{click}}$ | Average interval between clicks | 0.0 |
| `std_click_interval_ms` | `mouse_click` | ms | $\sigma(\Delta t_{\text{click}})$ | Regularity of click intervals | 0.0 |
| `min_click_interval_ms` | `mouse_click` | ms | $\min(\Delta t_{\text{click}})$ | Fastest click interval | 0.0 |
| `max_click_interval_ms` | `mouse_click` | ms | $\max(\Delta t_{\text{click}})$ | Slowest click interval | 0.0 |
| `double_click_rate` | `mouse_click` | ratio [0,1] | $\frac{\text{double\_clicks}}{\text{click\_count}}$ | Proportion of rapid double clicks | 0.0 |
| `button_click_ratio` | `mouse_click` | ratio [0,1] | $\frac{\text{button\_clicks}}{\text{click\_count}}$ | Proportion targeting `<button>` | 0.0 |
| `link_click_ratio` | `mouse_click` | ratio [0,1] | $\frac{\text{link\_clicks}}{\text{click\_count}}$ | Proportion targeting `<a>` links | 0.0 |
| `input_click_ratio` | `mouse_click` | ratio [0,1] | $\frac{\text{input\_clicks}}{\text{click\_count}}$ | Proportion targeting `<input>` / `<textarea>` | 0.0 |
| `other_click_ratio` | `mouse_click` | ratio [0,1] | $\frac{\text{other\_clicks}}{\text{click\_count}}$ | Proportion targeting generic DOM elements | 0.0 |

---

## Group C: Keyboard Dynamics (14 Features)

*STRICT PRIVACY: Extracted exclusively from event timing intervals. Zero keystroke characters or input values are ingested.*

| Feature Name | Source | Unit | Mathematical Definition | Interpretation | Missing Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `key_event_count` | `key_meta` | count | Total keypress events | Typing volume | 0.0 |
| `mean_dwell_ms` | `key_meta` | ms | $\frac{1}{K}\sum (t_{\text{keyup}} - t_{\text{keydown}})$ | Key hold duration | 0.0 |
| `std_dwell_ms` | `key_meta` | ms | $\sigma(\Delta t_{\text{dwell}})$ | Hold duration variance | 0.0 |
| `min_dwell_ms` | `key_meta` | ms | $\min(\Delta t_{\text{dwell}})$ | Minimum hold duration | 0.0 |
| `max_dwell_ms` | `key_meta` | ms | $\max(\Delta t_{\text{dwell}})$ | Maximum hold duration | 0.0 |
| `mean_flight_ms` | `key_meta` | ms | $\frac{1}{K}\sum (t_{\text{keydown}}^{i} - t_{\text{keyup}}^{i-1})$ | Flight time between keys | 0.0 |
| `std_flight_ms` | `key_meta` | ms | $\sigma(\Delta t_{\text{flight}})$ | Rhythm / cadence irregularity | 0.0 |
| `min_flight_ms` | `key_meta` | ms | $\min(\Delta t_{\text{flight}})$ | Shortest inter-key transition | 0.0 |
| `max_flight_ms` | `key_meta` | ms | $\max(\Delta t_{\text{flight}})$ | Longest transition pause | 0.0 |
| `mean_inter_key_interval_ms` | `key_meta` | ms | $\frac{1}{K}\sum (t_{\text{keydown}}^{i} - t_{\text{keydown}}^{i-1})$ | Mean keystroke period | 0.0 |
| `std_inter_key_interval_ms` | `key_meta` | ms | $\sigma(\Delta t_{\text{inter\_key}})$ | Keystroke period variance | 0.0 |
| `typing_speed` | `key_meta` | keys/s | $\frac{\text{key\_event\_count}}{\Delta t_{\text{session\_sec}}}$ | Aggregate typing throughput | 0.0 |
| `backspace_rate` | `key_meta` | ratio [0,1] | $\frac{\text{backspaces}}{\text{key\_event\_count}}$ | Error correction frequency | 0.0 |
| `paste_rate` | `key_meta` | ratio [0,1] | $\frac{\text{pastes}}{\text{key\_event\_count}}$ | Clipboard insertion frequency | 0.0 |

---

## Group D: Scroll Dynamics (10 Features)

| Feature Name | Source | Unit | Mathematical Definition | Interpretation | Missing Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scroll_event_count` | `scroll` | count | Total scroll sample bursts | Reading / scanning activity | 0.0 |
| `total_scroll_distance` | `scroll` | px | $\sum \sqrt{\Delta x^2 + \Delta y^2}$ | Total page travel distance | 0.0 |
| `mean_scroll_velocity` | `scroll` | px/s | $\frac{1}{S}\sum v_{\text{scroll}}$ | Average scrolling velocity | 0.0 |
| `std_scroll_velocity` | `scroll` | px/s | $\sigma(v_{\text{scroll}})$ | Scrolling smoothness | 0.0 |
| `max_scroll_velocity` | `scroll` | px/s | $\max(v_{\text{scroll}})$ | Maximum scrolling flick speed | 0.0 |
| `upward_scroll_ratio` | `scroll` | ratio [0,1] | $\frac{\text{up\_scrolls}}{\text{scroll\_count}}$ | Reviewing / re-reading content | 0.0 |
| `downward_scroll_ratio` | `scroll` | ratio [0,1] | $\frac{\text{down\_scrolls}}{\text{scroll\_count}}$ | Progressive content discovery | 0.0 |
| `scroll_direction_change_count` | `scroll` | count | Inversions between up and down | Reading oscillations | 0.0 |
| `mean_scroll_interval_ms` | `scroll` | ms | $\frac{1}{S}\sum \Delta t_{\text{scroll}}$ | Dwell time between scroll actions | 0.0 |
| `scroll_burst_count` | `scroll` | count | Continuous bursts separated by >200ms | Distinct reading epochs | 0.0 |

---

## Group E: Navigation Dynamics (9 Features)

| Feature Name | Source | Unit | Mathematical Definition | Interpretation | Missing Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `navigation_count` | `navigation` | count | Total route transitions | Page visit count | 0.0 |
| `unique_route_count` | `navigation` | count | Unique sanitized pathnames | Exploration diversity | 0.0 |
| `mean_page_dwell_ms` | `navigation` | ms | $\frac{1}{N}\sum \Delta t_{\text{page\_dwell}}$ | Average time per page view | 0.0 |
| `std_page_dwell_ms` | `navigation` | ms | $\sigma(\Delta t_{\text{page\_dwell}})$ | Dwell time variance | 0.0 |
| `min_page_dwell_ms` | `navigation` | ms | $\min(\Delta t_{\text{page\_dwell}})$ | Shortest page bounce time | 0.0 |
| `max_page_dwell_ms` | `navigation` | ms | $\max(\Delta t_{\text{page\_dwell}})$ | Longest page inspection time | 0.0 |
| `navigation_rate` | `navigation` | routes/s | $\frac{\text{navigation\_count}}{\Delta t_{\text{session\_sec}}}$ | Page transition velocity | 0.0 |
| `repeated_route_count` | `navigation` | count | Transitions revisiting known paths | Looping behavior | 0.0 |
| `route_repetition_ratio` | `navigation` | ratio [0,1] | $\frac{\text{repeated\_routes}}{\text{navigation\_count}}$ | Degree of route backtracking | 0.0 |

---

## Group F: Visibility & Focus (8 Features)

| Feature Name | Source | Unit | Mathematical Definition | Interpretation | Missing Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `visibility_event_count` | `visibility` | count | Total focus/blur/hidden state changes | Multitasking frequency | 0.0 |
| `hidden_event_count` | `visibility` | count | Tab backgrounded count | Tab switching count | 0.0 |
| `focus_event_count` | `visibility` | count | Window focus count | Window activation count | 0.0 |
| `blur_event_count` | `visibility` | count | Window blur count | Window deactivation count | 0.0 |
| `total_time_away_ms` | `visibility` | ms | $\sum \Delta t_{\text{away}}$ | Total duration outside the active tab | 0.0 |
| `mean_time_away_ms` | `visibility` | ms | $\frac{1}{V}\sum \Delta t_{\text{away}}$ | Average duration per distraction | 0.0 |
| `max_time_away_ms` | `visibility` | ms | $\max(\Delta t_{\text{away}})$ | Longest duration away from tab | 0.0 |
| `time_away_ratio` | `visibility` | ratio [0,1] | $\frac{\text{total\_time\_away}}{\Delta t_{\text{session}}}$ | Fraction of session spent in background | 0.0 |

---

## Group G: Cross-Behavior Session Metrics (8 Features)

| Feature Name | Source | Unit | Mathematical Definition | Interpretation | Missing Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `session_duration_ms` | Session | ms | $t_{\text{end}} - t_{\text{start}}$ | Overall session lifespan | 0.0 |
| `total_behavior_event_count` | Session | count | Total events ingested across all categories | Fleet telemetry volume | 0.0 |
| `events_per_second` | Session | events/s | $\frac{\text{total\_events}}{\Delta t_{\text{session\_sec}}}$ | Overall interaction intensity | 0.0 |
| `active_behavior_duration_ms` | Session | ms | Estimated active motor time | Engaged interaction lifespan | 0.0 |
| `interaction_density` | Session | events/s | $\frac{\text{total\_events}}{\Delta t_{\text{active\_sec}}}$ | Event density while user is active | 0.0 |
| `mouse_to_click_ratio` | Session | ratio | $\frac{\text{mouse\_events}}{\text{click\_count}}$ | Cursor movement per click action | 0.0 |
| `click_to_navigation_ratio` | Session | ratio | $\frac{\text{click\_count}}{\text{navigation\_count}}$ | Clicks per page visited | 0.0 |
| `navigation_to_session_ratio` | Session | routes/min | $\frac{\text{nav\_count}}{\Delta t_{\text{session\_min}}}$ | Page traversal cadence | 0.0 |
