# Fresh current mapped connectivity only; exact four LF first-D exceptions.
proc kwt_names97 {objects} {
 set names {};foreach_in_collection o $objects {lappend names [get_object_name $o]}
 return [lsort -unique $names]
}
proc kwt_pin97 {cell leaf} {
 set found {};foreach_in_collection p [get_pins -of_objects $cell] {
  if {[lindex [split [get_object_name $p] /] end] eq $leaf} {lappend found $p}
 }
 if {[llength $found]!=1} {error "Exact CDC pin absent/ambiguous"}
 return [lindex $found 0]
}
set cells97 [dict create];set first97 {}
foreach_in_collection c [get_cells -hierarchical -filter {is_hierarchical == false}] {
 set n [get_object_name $c]
 if {![string match {*r_ls_clk_sync_reg*} $n]} {continue}
 dict set cells97 $n $c
 if {[regexp {r_ls_clk_sync_reg\[0\]$} $n]} {lappend first97 $n}
}
if {[dict size $cells97]!=12||[llength $first97]!=4} {error "Exactly4 original3-stage chains required"}
set selected97 {};set out97 [open [file join $audit_out cdc_exact97.tsv] w]
puts $out97 "first_D\tfirst_Q\tsecond_D\tthird_D\tfirst_fanin\tfirst_Q_only_endpoint\tstage_clocks"
foreach n [lsort $first97] {
 set dp {};set qp {};set ck {}
 foreach k {0 1 2} {
  regsub {\[0\]$} $n [format {[%d]} $k] name
  if {![dict exists $cells97 $name]} {error "CDC stage missing"}
  set c [dict get $cells97 $name];set d [kwt_pin97 $c D];set q [kwt_pin97 $c Q];set clock [kwt_pin97 $c CK]
  if {[kwt_names97 [get_attribute $clock clocks]] ne [list core_clk]} {error "CDC stage clock mismatch"}
  lappend dp $d;lappend qp $q;lappend ck $clock
 }
 set d0 [lindex $dp 0];set q0 [lindex $qp 0];set d1 [lindex $dp 1];set d2 [lindex $dp 2]
 if {[kwt_names97 [all_fanin -to $d0 -flat -startpoints_only]] ne [list lfextclk]} {error "First D source mismatch"}
 if {[kwt_names97 [all_fanout -from $q0 -flat -endpoints_only]] ne [list [get_object_name $d1]]} {error "First Q must feed only second D"}
 if {[kwt_names97 [all_fanin -to $d1 -flat -startpoints_only]] ne [list [get_object_name [lindex $ck 0]]]} {error "Second D launch mismatch"}
 if {[kwt_names97 [all_fanin -to $d2 -flat -startpoints_only]] ne [list [get_object_name [lindex $ck 1]]]} {error "Third D launch mismatch"}
 lappend selected97 $d0
 puts $out97 [join [list [get_object_name $d0] [get_object_name $q0] [get_object_name $d1] [get_object_name $d2] lfextclk [get_object_name $d1] core_clk,core_clk,core_clk] "\t"]
}
close $out97
if {[llength $selected97]!=4} {error "CDC guard incomplete"}
foreach p $selected97 {set_false_path -from [get_ports lfextclk] -to $p}
redirect [file join $audit_out exceptions97.rpt] {report_exceptions}
puts {KWT_CDC97_EXACT_FOUR_FIRST_D_GUARDS_PASSED}
