use <holder.scad>
use <exits.scad>
part="holder_positive";
if(part=="holder_positive")scene0_relieved_holder();
if(part=="removed")scene0_relief_removed();
if(part=="nonplastic")intersection(){scene0_source_channel();scene0_other_parts_guard();}
if(part=="mount_posts")intersection(){scene0_source_channel();scene0_mount_posts_guard();}
if(part=="bearing_layer")intersection(){scene0_source_channel();scene0_bearing_layer_guard();}
if(part=="lead_bores")intersection(){scene0_source_channel();scene0_input_lead_bores_guard();}
if(part=="source_holder")intersection(){source_pair();scene0_relieved_holder();}
