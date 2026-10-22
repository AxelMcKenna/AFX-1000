#import <Cocoa/Cocoa.h>
#include "rmx/Panel.h"
#include <cmath>
#include <cstdio>

namespace {
constexpr double pi=3.14159265358979323846;
NSColor* rgb(unsigned hex,CGFloat alpha=1) { return [NSColor colorWithCalibratedRed:((hex>>16)&255)/255. green:((hex>>8)&255)/255. blue:(hex&255)/255. alpha:alpha]; }
void fill(NSRect r,unsigned hex,CGFloat radius=0) { [rgb(hex) setFill]; [[NSBezierPath bezierPathWithRoundedRect:r xRadius:radius yRadius:radius] fill]; }
void stroke(NSRect r,unsigned hex,CGFloat radius=0,CGFloat width=1) { auto* p=[NSBezierPath bezierPathWithRoundedRect:r xRadius:radius yRadius:radius]; [rgb(hex) setStroke];p.lineWidth=width;[p stroke]; }
void line(NSPoint a,NSPoint b,unsigned hex,CGFloat width=1) { auto* p=[NSBezierPath bezierPath];[p moveToPoint:a];[p lineToPoint:b];[rgb(hex) setStroke];p.lineWidth=width;[p stroke]; }
void label(NSString* s,NSRect r,CGFloat size,unsigned hex=0xc5cbd0,bool bold=false,NSTextAlignment align=NSTextAlignmentCenter) {
    auto* style=[NSMutableParagraphStyle new];style.alignment=align;
    [s drawInRect:r withAttributes:@{NSFontAttributeName:[NSFont monospacedSystemFontOfSize:size weight:bold?NSFontWeightBold:NSFontWeightRegular],NSForegroundColorAttributeName:rgb(hex),NSParagraphStyleAttributeName:style}];
}
NSString* string(std::string_view value) { return [[NSString alloc] initWithBytes:value.data() length:value.size() encoding:NSUTF8StringEncoding]; }
void circle(NSRect r,unsigned hex) { [rgb(hex) setFill];[[NSBezierPath bezierPathWithOvalInRect:r] fill]; }
void knob(const rmx::panel::Control& control) {
    const auto& r=control.rect;const CGFloat x=r.x+r.w/2,y=r.y+r.h/2,radius=r.w/2;
    for(int i=0;i<=20;++i) {const double angle=(-225+i*13.5)*pi/180;line({x+(radius+10)*std::cos(angle),y+(radius+10)*std::sin(angle)},{x+(radius+15)*std::cos(angle),y+(radius+15)*std::sin(angle)},i%5==0?0x7d8589:0x3b4348,i%5==0?2:1);}
    circle({r.x+3,r.y+7,r.w,r.h},0x080b0c);
    auto* shape=[NSBezierPath bezierPathWithOvalInRect:{r.x+2,r.y+2,r.w-4,r.h-4}];
    auto* gradient=[[NSGradient alloc] initWithStartingColor:rgb(0x414a50) endingColor:rgb(0x11171b)];[gradient drawInBezierPath:shape angle:90];
    [rgb(0x606b71) setStroke];shape.lineWidth=1.5;[shape stroke];
    circle({r.x+11,r.y+11,r.w-22,r.h-22},0x1a2227);
    const auto& info=rmx::parameters[static_cast<size_t>(control.param)];
    const double angle=(-225+270*(info.initial-info.min)/(info.max-info.min))*pi/180;
    line({x+radius*.53*std::cos(angle),y+radius*.53*std::sin(angle)},{x+radius*.82*std::cos(angle),y+radius*.82*std::sin(angle)},0xe9e9df,4);
}
void button(const rmx::panel::Control& c) {
    const auto& r=c.rect;const bool amber=c.param==rmx::Param::AutoTempo||c.param==rmx::Param::Quantize;
    fill({r.x,r.y+3,r.w,r.h},0x080c0d,7);fill({r.x+2,r.y+2,r.w-4,r.h-5},0x263237,6);stroke({r.x+3,r.y+3,r.w-6,r.h-8},amber?0xdea647:0x5aa99f,5,2);
    NSString* title=string(c.label);
    if(c.kind==rmx::panel::Kind::Choice) title=string(rmx::isolateNames[static_cast<size_t>(c.value)]);
    if(c.param==rmx::Param::Overdub)title=@"OVERDUB";
    if(c.param==rmx::Param::XHold)title=@"HOLD";
    label(title,{r.x+3,r.y+r.h*.31,r.w-6,r.h*.65},c.kind==rmx::panel::Kind::Pad?13:11,amber?0xf0bd66:0x8fdbcf,true);
}
void art() {
    fill({0,0,2048,921},0x10171b,24);stroke({3,3,2042,915},0x465258,22,3);
    fill({20,20,2008,881},0x172126,16);
    line({38,275},{2010,275},0x48565d,2);line({1132,300},{1132,854},0x3a484f,2);
    label(@"RMX / SOFTWARE EFFECTS UNIT",{48,36,780,29},19,0xd8dedf,true,NSTextAlignmentLeft);
    label(@"STEREO IN / STEREO OUT",{50,75,630,20},11,0x7f939b,false,NSTextAlignmentLeft);
    label(@"INPUT",{65,103,94,21},13);label(@"OUTPUT",{638,103,105,21},13);
    label(@"INPUT",{187,125,65,22},12,0x7f939b);label(@"OUTPUT",{180,209,72,22},12,0x7f939b);
    label(@"BPM",{929,116,110,25},17,0xe7b35d,true);
    label(@"NUDGE",{764,174,125,20},12,0x7f939b);
    label(@"ISOLATE FX",{205,282,370,32},22,0xcbd2d3,true,NSTextAlignmentLeft);
    label(@"SCENE FX",{1403,86,200,30},22,0xcbd2d3,true);
    label(@"FX SOURCE",{36,292,115,20},12,0x7f939b);
    label(@"LOW",{257,560,136,27},19,0xadc1c7,true);label(@"MID",{600,560,136,27},19,0xadc1c7,true);label(@"HI",{951,560,136,27},19,0xadc1c7,true);
    fill({38,582,1055,272},0x111b20,12);stroke({38,582,1055,272},0x34474e,12,2);
    label(@"X-PAD",{54,589,128,26},20,0x86c5b9,true,NSTextAlignmentLeft);
    label(@"LEVEL",{68,704,100,24},15);label(@"PITCH",{278,704,105,24},15);
    label(@"DELETE",{976,686,85,18},10,0x81949b);label(@"MUTE",{980,826,79,18},10,0x81949b);
    label(@"SUB 1",{1140,698,116,24},15,0xe7b35d,true);label(@"SUB 2",{1755,698,116,24},15,0x8fdbcf,true);
    label(@"TIME / SIZE",{1126,852,146,20},11,0x81949b);label(@"CHARACTER",{1744,852,146,20},11,0x81949b);
    for(int i=0;i<4;++i) {fill({488.+i*115,590,30,23},0x60baaa,3);label([NSString stringWithFormat:@"%d",i+1],{488.+i*115,593,30,20},12,0x101a1d,true);}
    for(const auto& c:rmx::panel::controls()) {
        if(c.kind==rmx::panel::Kind::Knob&&c.param!=rmx::Param::Tempo)knob(c);
        else if(c.kind==rmx::panel::Kind::Toggle||c.kind==rmx::panel::Kind::Choice||c.kind==rmx::panel::Kind::Pad||c.action==6||c.action==7||c.action==8||c.action==9) {
            if(c.param!=rmx::Param::UserSettings)button(c);
        }
    }
    fill({473,739,410,82},0x070e11,7);stroke({473,739,410,82},0x5c9c93,7,2);
    const auto defaults=rmx::ParameterStore{}.snapshot();
    for(int i=0;i<8;++i) {line({478.+i*51,746},{478.+i*51,765},0x587a7d,2);label(string(rmx::xPadBeatNames[rmx::xPadBeatChoice(defaults,static_cast<float>(i))]),{475.+i*51,775,47,22},12,0x86c5b9);}
    for(int i=0;i<10;++i) {
        const double middle=(i<5?-140.4+i*25.2:140.4-(i-5)*25.2),begin=(middle-12.1)*pi/180,end=(middle+12.1)*pi/180;
        auto* wedge=[NSBezierPath bezierPath];[wedge moveToPoint:{1503+193*std::cos(begin),466+193*std::sin(begin)}];
        for(int step=0;step<=30;++step){const double a=begin+(end-begin)*step/30;[wedge lineToPoint:{1503+320*std::cos(a),466+320*std::sin(a)}];}
        for(int step=30;step>=0;--step){const double a=begin+(end-begin)*step/30;[wedge lineToPoint:{1503+193*std::cos(a),466+193*std::sin(a)}];}[wedge closePath];
        [rgb(i<5?0x302c22:0x1d3435) setFill];[wedge fill];[rgb(i<5?0x866944:0x3d7e79) setStroke];wedge.lineWidth=2;[wedge stroke];
        const double a=middle*pi/180;label(string(rmx::sceneNames[static_cast<size_t>(i)]),{1503+254*std::cos(a)-91,466+254*std::sin(a)-10,182,24},12,i<5?0xe6b361:0x8fd1c5,true);
    }
    label(@"DEPTH",{1444,576,118,24},14,0x879ba3,true);
    label(@"DEFAULT   USER",{1798,120,139,23},11,0x9cafb5);
    label(@"RELEASE FX",{1848,242,162,26},17,0xd4dcdd,true);
    label(@"BACK SPIN",{1879,365,129,20},11,0x9cafb5);label(@"ECHO",{1879,384,129,20},11,0x9cafb5);label(@"VINYL BRAKE",{1879,403,129,20},11,0x9cafb5);
    fill({1884,430,113,105},0x060b0e,6);stroke({1884,430,113,105},0x475a60,6,2);fill({1891,435,99,30},0x58676b,8);
    label(@"PULL / RELEASE",{1849,546,165,20},10,0x81949b);
    label(@"RMX",{1748,52,220,56},46,0xe5e8e5,true,NSTextAlignmentRight);
    for(NSPoint p: {NSPoint{32,32},NSPoint{2016,32},NSPoint{32,889},NSPoint{2016,889}}) {circle({p.x-6,p.y-6,12,12},0x080c0e);line({p.x-3,p.y},{p.x+3,p.y},0x526167,1);}
}
}
int main(int argc,const char* argv[]) { @autoreleasepool {
    if(argc!=2){std::fprintf(stderr,"Usage: rmx_panel_art output.png\n");return 2;}
    NSBitmapImageRep* bitmap=[[NSBitmapImageRep alloc] initWithBitmapDataPlanes:nullptr pixelsWide:2048 pixelsHigh:921 bitsPerSample:8 samplesPerPixel:4 hasAlpha:YES isPlanar:NO colorSpaceName:NSCalibratedRGBColorSpace bytesPerRow:0 bitsPerPixel:0];
    auto* context=[NSGraphicsContext graphicsContextWithBitmapImageRep:bitmap];[NSGraphicsContext saveGraphicsState];[NSGraphicsContext setCurrentContext:context];
    NSAffineTransform* flip=[NSAffineTransform transform];[flip translateXBy:0 yBy:921];[flip scaleXBy:1 yBy:-1];[flip concat];
    [NSGraphicsContext setCurrentContext:[NSGraphicsContext graphicsContextWithCGContext:context.CGContext flipped:YES]];art();[NSGraphicsContext restoreGraphicsState];
    NSData* data=[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}];NSError* error=nil;
    if(![data writeToFile:[NSString stringWithUTF8String:argv[1]] options:NSDataWritingAtomic error:&error]){std::fprintf(stderr,"%s\n",error.localizedDescription.UTF8String);return 1;}
    return 0;
}}
