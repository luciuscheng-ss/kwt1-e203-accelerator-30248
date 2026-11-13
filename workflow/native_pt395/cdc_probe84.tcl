# Read-only actual mapped synchronizer observations. No exceptions applied.
set f [open [file join $audit_out cdc_candidates.tsv] w]
puts $f "cell\tref\tpin\tdirection\trole\trelated"
set count 0
foreach_in_collection c [get_cells -hierarchical -filter {is_hierarchical == false}] {
 set n [get_object_name $c]
 if {![string match {*r_ls_clk_sync_reg*} $n]} { continue }
 incr count
 set ref [get_attribute $c ref_name]
 foreach_in_collection pin [get_pins -of_objects $c] {
  set pn [get_object_name $pin]
  set leaf [lindex [split $pn /] end]
  set direction [get_attribute $pin direction]
  if {$direction eq "in" && $leaf eq "D"} {
   set names {}
   foreach_in_collection p [all_fanin -to $pin -flat -startpoints_only] { lappend names [get_object_name $p] }
   puts $f [join [list $n $ref $pn $direction D_fanin [join [lsort -unique $names] ,]] "\t"]
  }
  if {$direction eq "out"} {
   set names {}
   foreach_in_collection p [all_fanout -from $pin -flat -endpoints_only] { lappend names [get_object_name $p] }
   puts $f [join [list $n $ref $pn $direction Q_endpoints [join [lsort -unique $names] ,]] "\t"]
  }
  if {$direction eq "in" && ($leaf eq "CK" || $leaf eq "CLK" || $leaf eq "CP")} {
   set names {}
   foreach_in_collection p [get_attribute $pin clocks] { lappend names [get_object_name $p] }
   puts $f [join [list $n $ref $pn $direction CK_clocks [join [lsort -unique $names] ,]] "\t"]
  }
 }
}
close $f
puts "KWT_CDC_PROBE_REGISTER_CELLS $count"
