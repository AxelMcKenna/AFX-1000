#import <Cocoa/Cocoa.h>
#include "rmx/Panel.h"
#include <cmath>
#include <cstdio>
#include <cstdint>

// Original panel artwork. Coordinates are shared with both interactive editors.
// Material detail is baked once; meters, lamps and knob pointers stay dynamic.
namespace {
constexpr double pi=3.14159265358979323846;
constexpr unsigned amber=0xe9ad56,teal=0x7bc9bd;
NSColor* rgb(unsigned hex,CGFloat alpha=1) { return [NSColor colorWithCalibratedRed:((hex>>16)&255)/255. green:((hex>>8)&255)/255. blue:(hex&255)/255. alpha:alpha]; }
NSBezierPath* rounded(NSRect r,CGFloat radius=0) { return [NSBezierPath bezierPathWithRoundedRect:r xRadius:radius yRadius:radius]; }
void fill(NSRect r,unsigned hex,CGFloat radius=0) { [rgb(hex) setFill];[rounded(r,radius) fill]; }
void stroke(NSRect r,unsigned hex,CGFloat radius=0,CGFloat width=1) { auto* p=rounded(r,radius);[rgb(hex) setStroke];p.lineWidth=width;[p stroke]; }
void line(NSPoint a,NSPoint b,unsigned hex,CGFloat width=1,CGFloat alpha=1) { auto* p=[NSBezierPath bezierPath];[p moveToPoint:a];[p lineToPoint:b];[rgb(hex,alpha) setStroke];p.lineWidth=width;[p stroke]; }
void gradient(NSBezierPath* p,unsigned top,unsigned bottom) { auto* g=[[NSGradient alloc] initWithStartingColor:rgb(top) endingColor:rgb(bottom)];[g drawInBezierPath:p angle:90]; }
void gradient(NSRect r,unsigned top,unsigned bottom,CGFloat radius=0) { gradient(rounded(r,radius),top,bottom); }
void outline(NSBezierPath* p,unsigned hex,CGFloat width=1) { [rgb(hex) setStroke];p.lineWidth=width;[p stroke]; }
void label(NSString* s,NSRect r,CGFloat size,unsigned hex=0xc5c6c3,bool bold=false,NSTextAlignment align=NSTextAlignmentCenter) {
    auto* style=[NSMutableParagraphStyle new];style.alignment=align;style.lineBreakMode=NSLineBreakByWordWrapping;
    [s drawInRect:r withAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:size weight:bold?NSFontWeightBold:NSFontWeightMedium],NSForegroundColorAttributeName:rgb(hex),NSParagraphStyleAttributeName:style}];
}
NSString* string(std::string_view value) { return [[NSString alloc] initWithBytes:value.data() length:value.size() encoding:NSUTF8StringEncoding]; }
void circle(NSRect r,unsigned hex) { [rgb(hex) setFill];[[NSBezierPath bezierPathWithOvalInRect:r] fill]; }
void ellipse(NSRect r,unsigned top,unsigned bottom) { gradient([NSBezierPath bezierPathWithOvalInRect:r],top,bottom); }
void recessed(NSRect r,CGFloat radius=6) {
    gradient(NSInsetRect(r,-3,-3),0x080909,0x595c5d,radius+2);
    fill(r,0x080c0c,radius);stroke(NSInsetRect(r,1,1),0x030505,radius,2);
    line({r.origin.x+radius,r.origin.y+r.size.height-1},{NSMaxX(r)-radius,NSMaxY(r)-1},0x626566,1,.35);
}
void screw(NSPoint p) {
    circle({p.x-8,p.y-7,16,16},0x080909);ellipse({p.x-6,p.y-6,12,12},0x535758,0x161819);
    line({p.x-3,p.y+3},{p.x+3,p.y-3},0x020303,2);line({p.x-2,p.y-3},{p.x+3,p.y+2},0x111313,1);
}
void knob(const rmx::panel::Control& control) {
    const auto& r=control.rect;const CGFloat x=r.x+r.w/2,y=r.y+r.h/2,radius=r.w/2;
    for(int i=0;i<=30;++i) {
        const double angle=(-225+i*9)*pi/180;const bool major=i%5==0;
        line({x+(radius+9)*std::cos(angle),y+(radius+9)*std::sin(angle)},{x+(radius+(major?17:13))*std::cos(angle),y+(radius+(major?17:13))*std::sin(angle)},major?0xb8bcb8:0x646969,major?2:1);
    }
    // Recessed collar and a cast shadow below the rubber grip.
    ellipse({r.x-5,r.y-4,r.w+10,r.h+10},0x0a0b0b,0x676c6c);
    circle({r.x-3,r.y-2,r.w+6,r.h+6},0x080a0a);
    for(int i=9;i>0;--i) circle({r.x+i*.25,r.y+3+i*.6,r.w,r.h},0x090a0a);
    auto* grip=[NSBezierPath bezierPath];
    for(int i=0;i<192;++i) {
        const double angle=i*pi/96;const double edge=radius-2+(i%8<4?0:-1.6);
        NSPoint p={x+edge*std::cos(angle),y+edge*std::sin(angle)};
        if(i==0)[grip moveToPoint:p];else [grip lineToPoint:p];
    }
    [grip closePath];gradient(grip,0x626767,0x151818);outline(grip,0x080b0b,1.5);
    // Individual flutes catch the same overhead light as the cap.
    for(int i=0;i<48;++i) {
        const double angle=i*pi/24;
        line({x+(radius-8)*std::cos(angle),y+(radius-8)*std::sin(angle)},{x+(radius-2)*std::cos(angle),y+(radius-2)*std::sin(angle)},std::sin(angle)<0?0x858b89:0x090b0b,1.5,.5);
    }
    ellipse({r.x+9,r.y+9,r.w-18,r.h-18},0x8a8f8d,0x222626);
    ellipse({r.x+11,r.y+11,r.w-22,r.h-22},0x353a3a,0x141717);
    // Fine horizontal brushing inside the cap, clipped to its circular face.
    [NSGraphicsContext saveGraphicsState];[[NSBezierPath bezierPathWithOvalInRect:{r.x+12,r.y+12,r.w-24,r.h-24}] addClip];
    for(CGFloat row=r.y+13;row<r.y+r.h-12;row+=1.6) line({r.x+10,row},{r.x+r.w-10,row},0xa5afaa,.5,.07);
    [NSGraphicsContext restoreGraphicsState];
    // The white position mark is drawn by the editors without rotating lighting.
}
void button(const rmx::panel::Control& c) {
    const auto& r=c.rect;const bool amberButton=c.param==rmx::Param::AutoTempo||c.param==rmx::Param::Quantize;
    const unsigned tint=amberButton?amber:teal;const bool pad=c.kind==rmx::panel::Kind::Pad;
    fill({r.x-2,r.y-1,r.w+4,r.h+6},0x080909,6);
    gradient({r.x,r.y,r.w,r.h},0x777e7c,0x1d2222,5);
    gradient({r.x+3,r.y+3,r.w-6,r.h-7},pad?0x535c5a:0x454b4b,pad?0x282f2e:0x202626,3);
    line({r.x+6,r.y+4},{r.x+r.w-6,r.y+4},0xb3bbb6,1,.7);
    line({r.x+5,r.y+r.h-5},{r.x+r.w-5,r.y+r.h-5},0x080b0b,2);
    gradient({r.x+8,r.y+r.h-9,r.w-16,3},tint,amberButton?0x8d591d:0x365d57,1);
    NSString* title=[string(c.label) uppercaseString];
    if(c.kind==rmx::panel::Kind::Choice) {
        constexpr std::array<std::string_view,4> titles{"ISOLATOR","CUT / ADD","TRANS / ROLL","GATE / DRIVE"};title=string(titles[static_cast<size_t>(c.value)]);
    }
    if(c.param==rmx::Param::Overdub)title=@"OVER\nDUB";
    if(c.param==rmx::Param::XHold)title=@"HOLD";
    if(c.action==7)title=c.value<0?@"−":@"+";
    const CGFloat font=c.action==7?23:pad?13:c.kind==rmx::panel::Kind::Choice?10.5:11;
    label(title,{r.x+4,r.y+(c.param==rmx::Param::Overdub?8:r.h*.26),r.w-8,r.h-8},font,pad?0xe5e9e2:0xd8ded8,true);
}
NSBezierPath* sector(double inner,double outer,double start,double end) {
    auto* p=[NSBezierPath bezierPath];
    for(int i=0;i<=60;++i) {const double a=(start+(end-start)*i/60)*pi/180;NSPoint point={1503+outer*std::cos(a),466+outer*std::sin(a)};if(i==0)[p moveToPoint:point];else[p lineToPoint:point];}
    for(int i=60;i>=0;--i) {const double a=(start+(end-start)*i/60)*pi/180;[p lineToPoint:{1503+inner*std::cos(a),466+inner*std::sin(a)}];}
    [p closePath];return p;
}
void art() {
    gradient({0,0,2048,921},0x737878,0x151819,26);stroke({2,2,2044,917},0x030505,25,3);
    gradient({9,9,2030,903},0x141818,0x050707,21);
    gradient({20,19,2008,881},0x373b3b,0x171a1a,13);
    stroke({20,19,2008,881},0x757b79,13,1);stroke({23,22,2002,875},0x101313,11,2);
    // Deterministic, restrained metal grain. No per-frame texture generation.
    [NSGraphicsContext saveGraphicsState];[rounded({25,25,1998,871},9) addClip];
    uint32_t noise=0x524d5831;
    for(int row=25;row<898;++row) {
        noise=noise*1664525u+1013904223u;const CGFloat a=.004+(noise&255)/255.*.014;
        line({25.,row+.5},{2023.,row+.5},row%3?0xffffff:0x000000,.65,a);
    }
    [NSGraphicsContext restoreGraphicsState];
    // Engraved dividers and the inset sampler section.
    line({40,274},{1204,274},0x0a0d0d,2);line({40,276},{1204,276},0x707572,1,.5);
    line({1131,303},{1131,858},0x080b0b,2);line({1133,303},{1133,858},0x747975,1,.45);
    recessed({38,582,1055,272},8);gradient({42,587,1047,261},0x252b2b,0x171b1b,6);
    line({54,617},{1075,617},0x7a8580,1,.3);
    label(@"RMX",{50,41,210,52},45,0xe6e8e2,true,NSTextAlignmentLeft);
    label(@"REMIX STATION",{211,54,300,28},18,0x919b97,true,NSTextAlignmentLeft);
    label(@"INPUT",{65,102,94,21},13);label(@"OUTPUT",{638,102,105,21},13);
    label(@"INPUT",{187,124,65,22},12,0xb0b8b2);label(@"OUTPUT",{180,208,72,22},12,0xb0b8b2);
    recessed({259,119,376,31},4);recessed({259,203,376,31},4);
    label(@"−∞     −24      −12       −6       0    +6",{265,158,366,20},10,0x858f89);
    recessed({920,142,129,74},4);
    label(@"BPM",{929,116,110,25},17,0xd9dfd9,true);
    label(@"NUDGE",{764,174,125,20},11,0xa3ada6);
    label(@"ISOLATE FX",{204,287,370,32},22,0xe4e8df,true,NSTextAlignmentLeft);
    label(@"SCENE FX",{1403,85,200,30},24,0xe4e8df,true);
    label(@"FX SOURCE",{36,292,115,20},11,0xabb4ae);
    label(@"LOW",{257,559,136,27},18,0xd6ddd4,true);label(@"MID",{600,559,136,27},18,0xd6ddd4,true);label(@"HI",{951,559,136,27},18,0xd6ddd4,true);
    label(@"X-PAD FX",{54,588,180,27},21,0xcbd9d0,true,NSTextAlignmentLeft);
    label(@"LEVEL",{68,704,100,24},13);label(@"PITCH",{278,704,105,24},13);
    label(@"DELETE",{976,686,85,18},10,0x929c95);label(@"MUTE",{980,826,79,18},10,0x929c95);
    label(@"SUB PARAMETER",{1333,832,340,25},12,0x9aa59d,true);
    label(@"TIME / SIZE",{1126,852,146,20},11,0x9aa59d);label(@"CHARACTER",{1744,852,146,20},11,0x9aa59d);
    label(@"SUB 1",{1140,697,116,24},13,amber,true);label(@"SUB 2",{1755,697,116,24},13,teal,true);
    for(int i=0;i<4;++i) {recessed({488.+i*115,590,30,23},3);label([NSString stringWithFormat:@"%d",i+1],{488.+i*115,592,30,20},12,teal,true);}
    // Broad physical button caps around a recessed ring, with separate light pipes.
    for(int i=0;i<10;++i) {
        const double middle=i<5?-140.4+i*25.2:140.4-(i-5)*25.2;
        const double begin=middle-12.1,end=middle+12.1;const unsigned tint=i<5?amber:teal;
        auto* surround=sector(187,326,begin-.4,end+.4);gradient(surround,0x070909,0x0e1110);outline(surround,0x707774,1);
        auto* bezel=sector(193,320,begin,end);gradient(bezel,0x8b9390,0x282e2d);outline(bezel,0x111615,1.5);
        auto* face=sector(198,315,begin+.65,end-.65);gradient(face,0x424b47,0x212824);outline(face,0x0e1512,1);
        auto* pipe=sector(199,204,begin+1.4,end-1.4);gradient(pipe,tint,i<5?0x6d4924:0x284b40);
        const double a=middle*pi/180;
        label([string(rmx::sceneNames[static_cast<size_t>(i)]) uppercaseString],{1503+257*std::cos(a)-84,466+257*std::sin(a)-9,168,24},12,i<5?0xf0cca1:0xa5d6c3,true);
    }
    for(const auto& c:rmx::panel::controls()) {
        if(c.kind==rmx::panel::Kind::Knob&&c.param!=rmx::Param::Tempo)knob(c);
        else if(c.kind==rmx::panel::Kind::Toggle||c.kind==rmx::panel::Kind::Choice||c.kind==rmx::panel::Kind::Pad||c.action==6||c.action==7||c.action==8||c.action==9) {
            if(c.param!=rmx::Param::UserSettings)button(c);
        }
    }
    label(@"DEPTH",{1444,575,118,24},13,0xc1cdc3,true);
    recessed({473,739,410,82},5);
    gradient({477,743,402,74},0x26322f,0x0a1210,3);
    for(int i=0;i<8;++i)line({478.+i*51,747},{478.+i*51,765},0x8ab8a6,1.5);
    label(@"DEFAULT   USER",{1798,120,139,23},11,0xadb8ae);
    label(@"RELEASE FX",{1848,242,162,26},17,0xe4e8df,true);
    label(@"BACK SPIN",{1879,365,129,20},11,0xb1bcb2);label(@"ECHO",{1879,384,129,20},11,0xb1bcb2);label(@"VINYL BRAKE",{1879,403,129,20},11,0xb1bcb2);
    recessed({1884,430,113,105},6);
    gradient({1891,435,99,30},0xb6bfba,0x424a46,5);stroke({1891,435,99,30},0x121b16,5,1);
    for(int i=0;i<4;++i)line({1902,442.+i*5},{1978,442.+i*5},i%2?0x333c36:0xc4ccc5,1);
    label(@"PULL / RELEASE",{1849,546,165,20},10,0x9aa59d);
    gradient({1841,590,160,62},0x404744,0x151c18,3);stroke({1841,590,160,62},0x66726a,3,1);
    label(@"STEREO",{1854,602,134,18},11,0xa6b7a9,true);label(@"PERFORMANCE FX",{1854,622,134,17},11,0xd7e1d6,true);
    label(@"STEREO / REAL-TIME PROCESSING",{1743,62,253,21},11,0x909e93,false,NSTextAlignmentRight);
    for(NSPoint p:{NSPoint{32,32},NSPoint{2016,32},NSPoint{32,889},NSPoint{2016,889}})screw(p);
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
