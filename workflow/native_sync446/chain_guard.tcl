set cells [dict create]
foreach_in_collection c [get_cells -hierarchical -filter {is_hierarchical == false && (full_name =~ *irq_sync* || full_name =~ *rtctoggle_sync*)}] {dict set cells [get_object_name $c] $c}
proc pin436 {cell leaf} {
 set out {};foreach_in_collection p [get_pins -of_objects $cell] {if {[lindex [split [get_object_name $p] /] end] eq $leaf} {lappend out $p}}
 if {[llength $out]!=1} {error "Missingexactpin"}
 return [lindex $out 0]
}
foreach name $firsts {
 set cellname [join [lrange [split $name /] 0 end-1] /]
 if {![dict exists $cells $cellname]} {error "Missingfirststage"}
 set c [dict get $cells $cellname];set d [pin436 $c D];set q [pin436 $c Q];set ck [pin436 $c CK]
 if {[get_object_name [get_attribute $ck clocks]] ne "core_clk"} {error "Firststageclock"}
 set ends [all_fanout -from $q -flat -endpoints_only]
 if {[sizeof_collection $ends]!=1} {error "FirstQ has extra functionalconsumer"}
 set second [get_object_name $ends]
 if {![regexp {sync_gen\[1\]} $second]||![string match */D $second]} {error "NotsecondstageD"}
 set c2 [get_cells -of_objects $ends];set ck2 [pin436 $c2 CK]
 if {[get_object_name [get_attribute $ck2 clocks]] ne "core_clk"} {error "Secondstageclock"}
 set starts [all_fanin -to $d -flat -startpoints_only]
 if {[sizeof_collection $starts]!=1} {error "UnexpectedfirstDfanin"}
 set slacks {}
 foreach typ {max min} {
  set ps [get_timing_paths -from $q -to $ends -delay_type $typ -max_paths 1 -slack_lesser_than 1000000]
  if {[sizeof_collection $ps]!=1} {error "Interstagetimingmissing"}
  set s [get_attribute $ps slack];if {$s<0} {error "Interstagedelayfailed"}
  lappend slacks $s
 }
 puts $f [join [list $name [get_object_name $q] $second [get_object_name $starts] {*}$slacks] "\t"]
}
close $f
puts {KWT_SINGLEBIT436_PASS}
quit
