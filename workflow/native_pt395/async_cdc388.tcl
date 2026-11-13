# The two physical oscillators are asynchronous. Original two-stage four-phase
# ICB CDC holds bundled data until receiver acceptance returns; no periodic
# phase relation is assumed. Bound each transfer by one receiving-domain cycle
# minus0.1ns, retaining normal same-domain setup/hold and all four old guarded
# first-D exceptions. No asynchronous clock-group false path is introduced.
if {abs([get_attribute [get_clocks core_clk] period]-6.666666666667)>1e-6} {error "ActualHFperiod changed"}
if {abs([get_attribute [get_clocks lf_clk] period]-30517.578125)>1e-6} {error "ActualLFperiod changed"}
foreach_in_collection c [all_registers -clock lf_clk] {if {[string match {*u_kwt*} [get_object_name $c]]} {error "New accelerator has unreviewed LF register"}}
set_max_delay 30517.478125 -ignore_clock_latency -from [get_clocks core_clk] -to [get_clocks lf_clk]
set_min_delay 0.0 -ignore_clock_latency -from [get_clocks core_clk] -to [get_clocks lf_clk]
set_max_delay 6.566666666667 -ignore_clock_latency -from [get_clocks lf_clk] -to [get_clocks core_clk]
set_min_delay 0.0 -ignore_clock_latency -from [get_clocks lf_clk] -to [get_clocks core_clk]
# Identify and prove slow-only control output ownership before assigning its IO
# constraints to the actual LF domain. Numerical IO setup/hold values unchanged.
set kwt_slow_output_ports [filter_collection [all_fanout -from [all_registers -clock lf_clk -output_pins] -flat -endpoints_only] {object_class == port}]
if {[sizeof_collection $kwt_slow_output_ports]<1||[sizeof_collection $kwt_slow_output_ports]>32} {error "Unexpected slow-output port count"}
set kwt_slow_output_proof {}
foreach_in_collection p $kwt_slow_output_ports {
 set cls {};set starts {}
 foreach_in_collection sp [all_fanin -to $p -flat -startpoints_only] {
  lappend starts [get_object_name $sp]
  foreach_in_collection cl [get_attribute -quiet $sp clocks] {lappend cls [get_object_name $cl]}
 }
 set cls [lsort -unique $cls]
 if {$cls ne [list lf_clk]} {error "Slow output has an unreviewed mixed/unknown clock source"}
 lappend kwt_slow_output_proof [list [get_object_name $p] $cls $starts]
}
remove_output_delay $kwt_slow_output_ports
set_output_delay -max 2.0 -clock lf_clk $kwt_slow_output_ports
set_output_delay -min 0.2 -clock lf_clk $kwt_slow_output_ports
