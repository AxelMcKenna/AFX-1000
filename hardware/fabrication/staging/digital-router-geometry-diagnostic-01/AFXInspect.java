import app.freerouting.core.RoutingJob;
import app.freerouting.management.HeadlessBoardManager;
import app.freerouting.board.facade.RoutingBoard;
import app.freerouting.board.model.items.*;
import app.freerouting.drc.ClearanceViolation;
import com.google.gson.GsonBuilder;
import java.nio.file.*;
import java.io.*;
import java.util.*;

public class AFXInspect {
  static Map<String,Object> item(Item i, RoutingBoard b) {
    var row = new LinkedHashMap<String,Object>();
    row.put("id",i.getId()); row.put("kind",i.getClass().getSimpleName());
    row.put("fixed",i.isUserFixed());
    var nets = new ArrayList<String>();
    for(int k=0;k<i.netCount();k++) nets.add(b.rules.nets.get(i.getNetNumber(k)).name);
    row.put("nets",nets);
    if(i instanceof DrillItem d) {
      row.put("xy",new double[]{d.getCenter().toFloat().x,d.getCenter().toFloat().y});
      row.put("padstack",d.getPadstack().name);
      row.put("drill_radius",d.getPadstack().getDrillRadius());
    }
    if(i instanceof Pin p) {
      row.put("component",b.components.get(p.getComponentId()).name);
      row.put("pin_index",p.getPinIndex());
    }
    if(i instanceof Trace t) {
      row.put("start",new double[]{t.firstCorner().toFloat().x,t.firstCorner().toFloat().y});
      row.put("end",new double[]{t.lastCorner().toFloat().x,t.lastCorner().toFloat().y});
      row.put("half_width",t.getHalfWidth());
    }
    return row;
  }
  public static void main(String[] args) throws Exception {
    var job = new RoutingJob();
    job.routerSettings.holeClearanceUm=Double.valueOf(args[2]);
    job.routerSettings.copperToEdgeClearanceUm=500.;
    job.routerSettings.clearanceToleranceUm=0.;
    job.routerSettings.planeAsObstacle=false;
    var manager = new HeadlessBoardManager(job);
    try(var stream=new FileInputStream(args[0])) {manager.loadFromSpecctraDsn(stream,null,null);}
    RoutingBoard b=manager.getRoutingBoard();
    if(b==null) throw new IllegalStateException("No loaded board");
    if(b.postLoadFuture!=null) b.postLoadFuture.join();
    var seen=new HashSet<String>(); var rows=new ArrayList<Map<String,Object>>();
    for(var v:ClearanceViolation.aggregateSortedBySeverity(b.getItems())) {
      String key=Math.min(v.firstItem.getId(),v.secondItem.getId())+":"+Math.max(v.firstItem.getId(),v.secondItem.getId())+":"+v.layer;
      if(!seen.add(key))continue;
      var row=new LinkedHashMap<String,Object>();
      row.put("first",item(v.firstItem,b)); row.put("second",item(v.secondItem,b));
      row.put("layer",v.layer);row.put("expected",v.expectedClearance);row.put("actual",v.actualClearance);
      row.put("same_net",v.firstItem.sharesNet(v.secondItem));
      rows.add(row);
    }
    var output=new LinkedHashMap<String,Object>();
    output.put("resolution",b.communication.resolution);output.put("unit",b.communication.unit.toString());
    output.put("hole_override_um",args[2]);output.put("violations",rows);
    Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().create().toJson(output));
    System.out.println("Captured "+rows.size()+" distinct item-pair/layer findings");
  }
}
