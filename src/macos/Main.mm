#import <Cocoa/Cocoa.h>
#import <AVFoundation/AVFoundation.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#include "AudioHost.h"
#include "rmx/State.h"
#include "rmx/Wav.h"
#include "rmx/Panel.h"
#include "rmx/Skin.h"
#include "rmx/PanelController.h"
#include <filesystem>
#include <memory>
#include <sstream>

namespace {
using rmx::Param;
NSColor* color(float r,float g,float b,float a=1) { return [NSColor colorWithCalibratedRed:r green:g blue:b alpha:a]; }
NSColor* orange() { return color(1,.43,.16); }
NSColor* cyan() { return color(.18,.82,.87); }
NSColor* muted() { return color(.47,.51,.56); }
void box(NSRect r,NSColor* fill,CGFloat radius=10) { [fill setFill]; [[NSBezierPath bezierPathWithRoundedRect:r xRadius:radius yRadius:radius] fill]; }
void text(NSString* s,NSRect r,CGFloat size,NSColor* c,bool bold=false,NSTextAlignment alignment=NSTextAlignmentLeft) {
    NSMutableParagraphStyle* style=[NSMutableParagraphStyle new]; style.alignment=alignment;
    [s drawInRect:r withAttributes:@{NSFontAttributeName:bold?[NSFont boldSystemFontOfSize:size]:[NSFont systemFontOfSize:size],NSForegroundColorAttributeName:c,NSParagraphStyleAttributeName:style}];
}
NSString* str(std::string_view s) { return [[NSString alloc] initWithBytes:s.data() length:s.size() encoding:NSUTF8StringEncoding]; }
NSString* valueText(Param p,float v) {
    if(p==Param::SceneTime) return [NSString stringWithFormat:@"%.0f%%",v/7*100];
    if(p==Param::XRoll) return str(rmx::xPadPositionNames[static_cast<size_t>(rmx::sanitize(p,v))]);
    if(p==Param::Tempo) return [NSString stringWithFormat:@"%.1f",v];
    if(p==Param::ReleaseTime) return [NSString stringWithFormat:@"%.2f beats",v];
    if(p==Param::XPitch) return [NSString stringWithFormat:@"%+.1f st",v];
    if(p==Param::InputGain||p==Param::OutputGain) return [NSString stringWithFormat:@"%+.1f dB",v];
    if(p==Param::Low||p==Param::Mid||p==Param::High) return std::abs(v)<.005?@"0":[NSString stringWithFormat:@"%+.0f%%",v*100];
    if(p==Param::LowCrossover||p==Param::HighCrossover) return [NSString stringWithFormat:@"%.0f Hz",v];
    return [NSString stringWithFormat:@"%.0f%%",v*100];
}
using Kind=rmx::panel::Kind;
struct Control { NSRect rect; Kind kind; Param param; std::string label; float value{}; int action{}; };
std::filesystem::path sessionPath() {
    NSString* folder=[NSSearchPathForDirectoriesInDomains(NSApplicationSupportDirectory,NSUserDomainMask,YES) firstObject];
    auto path=std::filesystem::path(folder.UTF8String)/"RMX"; std::filesystem::create_directories(path); return path/"session.rmx";
}
}

@interface SetupView : NSView
@end
@implementation SetupView
- (BOOL)isFlipped { return YES; }
@end

@class Surface;
@interface RMXControlElement : NSView
@property(nonatomic,weak) Surface* surface;
@property(nonatomic) NSInteger controlIndex;
@end

@interface Surface : NSView {
@public
    rmx::Engine* engine;
    AudioHost* host;
    rmx::SampleBank* bank;
    std::shared_ptr<rmx::Engine> engineOwner;
    std::shared_ptr<AudioHost> hostOwner;
    std::shared_ptr<rmx::SampleBank> bankOwner;
    dispatch_queue_t audioQueue;
    BOOL audioStarting;
    rmx::State state;
    std::vector<Control> controls;
    std::vector<AudioDevice> devices;
    std::vector<MidiSource> sources;
    NSPopUpButton *inputMenu,*outputMenu,*inputPair,*outputPair,*bufferMenu,*midiMenu;
    NSButton *startButton,*linkButton;
    NSTextField *deviceStatus;
    int dragging;
    float dragStart;
    NSPoint dragOrigin;
    int selectedPad;
    int editSlot;
    NSString* message;
    NSTimer* timer;
    NSImage* panelImage;
    NSPanel* setupPanel;
    double tapTime;
}
- (instancetype)initWithEngine:(std::shared_ptr<rmx::Engine>)e host:(std::shared_ptr<AudioHost>)h bank:(std::shared_ptr<rmx::SampleBank>)b;
- (void)refreshDevices;
- (void)audioSetup:(id)sender;
- (void)editSample:(id)sender;
- (void)startAudio:(id)sender;
- (void)savePreset:(id)sender;
- (void)loadPreset:(id)sender;
- (void)importSample:(id)sender;
- (void)settings:(id)sender;
- (void)routingGuide:(id)sender;
- (void)update;
- (void)persist;
- (void)activateControlIndex:(NSInteger)index;
- (void)change:(Param)p value:(float)v;
- (void)sendEvent:(rmx::Event)event;
@end

@implementation RMXControlElement
- (BOOL)isAccessibilityElement { return YES; }
- (NSView*)hitTest:(NSPoint)point { (void)point; return nil; }
- (id)accessibilityMinValue { Surface* s=self.surface; if(!s||self.controlIndex>=static_cast<NSInteger>(s->controls.size())) return @0; const auto p=s->controls[static_cast<size_t>(self.controlIndex)].param; return p==Param::Count?@0:@(rmx::parameters[static_cast<size_t>(p)].min); }
- (id)accessibilityMaxValue { Surface* s=self.surface; if(!s||self.controlIndex>=static_cast<NSInteger>(s->controls.size())) return @1; const auto p=s->controls[static_cast<size_t>(self.controlIndex)].param; return p==Param::Count?@1:@(rmx::parameters[static_cast<size_t>(p)].max); }
- (id)accessibilityValue {
    Surface* s=self.surface; if(!s) return @0;
    if(self.controlIndex>=static_cast<NSInteger>(s->controls.size())) { const int scene=static_cast<int>(self.controlIndex-s->controls.size()); return @(s->engine->params.get(Param::SceneOn)>.5f&&static_cast<int>(s->engine->params.get(Param::SceneType))==scene); }
    const auto& c=s->controls[static_cast<size_t>(self.controlIndex)];
    if(c.kind==Kind::Choice) return @(s->engine->params.get(c.param)==c.value);
    if(c.kind==Kind::Pad) return @(s->selectedPad==static_cast<int>(c.value));
    return c.param==Param::Count?@0:@(s->engine->params.get(c.param));
}
- (void)setAccessibilityValue:(id)value {
    Surface* s=self.surface; if(!s||self.controlIndex>=static_cast<NSInteger>(s->controls.size())) return;
    const auto& c=s->controls[static_cast<size_t>(self.controlIndex)];
    if(c.kind==Kind::Knob||c.kind==Kind::Strip||c.kind==Kind::Lever) { [s change:c.param value:[value floatValue]]; if(c.param==Param::SceneDepth) [s change:Param::SceneOn value:1]; }
}
- (BOOL)accessibilityPerformPress { [self.surface activateControlIndex:self.controlIndex]; return YES; }
- (BOOL)accessibilityPerformIncrement { [self adjust:1]; return YES; }
- (BOOL)accessibilityPerformDecrement { [self adjust:-1]; return YES; }
- (void)adjust:(float)direction {
    Surface* s=self.surface; if(!s||self.controlIndex>=static_cast<NSInteger>(s->controls.size())) return;
    const auto& c=s->controls[static_cast<size_t>(self.controlIndex)]; if(c.param==Param::Count) return;
    const auto& p=rmx::parameters[static_cast<size_t>(c.param)]; [self setAccessibilityValue:@(s->engine->params.get(c.param)+direction*(p.discrete?1:(p.max-p.min)/100))];
}
@end

@implementation Surface
- (BOOL)isFlipped { return YES; }
- (BOOL)acceptsFirstResponder { return YES; }
- (void)sendEvent:(rmx::Event)event {
    if(host->running()) { engine->enqueue(event); return; }
    if(event.type==rmx::EventType::Tap) {
        const double now=NSDate.timeIntervalSinceReferenceDate;
        if(tapTime>0&&now>tapTime) { const double bpm=60/(now-tapTime); if(bpm>=40&&bpm<=240) { [self change:Param::Tempo value:static_cast<float>(bpm)]; [self change:Param::AutoTempo value:0]; } }
        tapTime=now;
    } else if(event.type==rmx::EventType::Panic) {
        for(auto p:{Param::SceneOn,Param::Low,Param::Mid,Param::High,Param::ReleaseAmount,Param::XHold,Param::Overdub}) [self change:p value:0];
    } else engine->enqueue(event);
}
- (BOOL)isAccessibilityElement { return YES; }
- (NSString*)accessibilityRole { return NSAccessibilityGroupRole; }
- (NSString*)accessibilityLabel { return @"RMX performance controls"; }
- (void)installAccessibleControls {
    auto add=[&](NSInteger index,NSString* label,NSRect area,bool slider) {
        RMXControlElement* element=[RMXControlElement new]; element.surface=self; element.controlIndex=index;
        element.accessibilityRole=slider?NSAccessibilitySliderRole:NSAccessibilityButtonRole; element.accessibilityLabel=label;
        area.origin.x*=self.bounds.size.width/2048; area.size.width*=self.bounds.size.width/2048; area.origin.y*=self.bounds.size.height/921; area.size.height*=self.bounds.size.height/921;
        element.frame=area; [self addSubview:element];
    };
    for(size_t i=0;i<controls.size();++i) { const auto& c=controls[i]; add(static_cast<NSInteger>(i),str(c.label),c.rect,c.kind==Kind::Knob||c.kind==Kind::Strip||c.kind==Kind::Lever); }
    for(int i=0;i<10;++i) { const double angle=(i<5?-140.4+i*25.2:140.4-(i-5)*25.2)*3.141592653589793/180; add(static_cast<NSInteger>(controls.size()+i),str(rmx::sceneNames[static_cast<size_t>(i)]),{1503+250*std::cos(angle)-40,466+250*std::sin(angle)-30,80,60},false); }
}
- (void)activateControlIndex:(NSInteger)index {
    if(index>=static_cast<NSInteger>(controls.size())) { const int scene=static_cast<int>(index-controls.size()); const bool same=static_cast<int>(engine->params.get(Param::SceneType))==scene&&engine->params.get(Param::SceneOn)>.5f; [self change:Param::SceneType value:static_cast<float>(scene)]; [self change:Param::SceneOn value:same?0:1]; return; }
    const auto& c=controls[static_cast<size_t>(index)]; if(c.kind==Kind::Pad) selectedPad=static_cast<int>(c.value);
    rmx::panel::Control model{{static_cast<float>(c.rect.origin.x),static_cast<float>(c.rect.origin.y),static_cast<float>(c.rect.size.width),static_cast<float>(c.rect.size.height)},c.kind,c.param,c.label,c.value,c.action};
    const bool handled=rmx::panel::activate(model,[&](Param p){return engine->params.get(p);},[&](Param p,float v){[self change:p value:v];},[&](rmx::Event e){[self sendEvent:e];});
    if(!handled&&c.action==1) [self settings:nil]; [self setNeedsDisplay:YES];
}
- (instancetype)initWithEngine:(std::shared_ptr<rmx::Engine>)e host:(std::shared_ptr<AudioHost>)h bank:(std::shared_ptr<rmx::SampleBank>)b {
    if((self=[super initWithFrame:NSMakeRect(0,0,1280,575.625)])) {
        engineOwner=e; hostOwner=h; bankOwner=b; engine=e.get(); host=h.get(); bank=b.get(); audioQueue=dispatch_queue_create("nz.axelmckenna.rmx.audio-control",DISPATCH_QUEUE_SERIAL); audioStarting=NO; dragging=-1; selectedPad=0; editSlot=0; message=@"Select audio devices, then start. Space: bypass · 1–4: drums · T: tap · Esc: reset";
        self.wantsLayer=YES; self.layer.backgroundColor=color(.035,.043,.055).CGColor;
        panelImage=[[NSImage alloc] initWithContentsOfFile:[NSBundle.mainBundle pathForResource:@"panel" ofType:@"png"]];
        for(const auto& c:rmx::panel::controls()) controls.push_back({{c.rect.x,c.rect.y,c.rect.w,c.rect.h},c.kind,c.param,c.label,c.value,c.action});
        [self installAccessibleControls];
        setupPanel=[[NSPanel alloc] initWithContentRect:{0,0,1280,220} styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];
        setupPanel.title=@"RMX · Audio & MIDI setup"; setupPanel.appearance=[NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
        setupPanel.contentView=[[SetupView alloc] initWithFrame:{0,0,1280,220}];
        auto popup=[&](NSRect r,SEL action) { NSPopUpButton* button=[[NSPopUpButton alloc] initWithFrame:r pullsDown:NO]; button.font=[NSFont systemFontOfSize:11]; button.target=self; button.action=action; [setupPanel.contentView addSubview:button]; return button; };
        inputMenu=popup({83,52,278,25},@selector(deviceChanged:)); outputMenu=popup({83,90,278,25},@selector(deviceChanged:));
        inputPair=popup({371,52,115,25},nullptr); outputPair=popup({371,90,115,25},nullptr);
        bufferMenu=popup({563,52,100,25},nullptr); for(auto v:{64,128,256,512,1024}) [bufferMenu addItemWithTitle:[NSString stringWithFormat:@"%d",v]]; [bufferMenu selectItemAtIndex:1];
        midiMenu=popup({742,52,270,25},@selector(midiChanged:));
        linkButton=[NSButton checkboxWithTitle:AudioHost::linkAvailable()?@"Ableton Link":@"Ableton Link (SDK not included)" target:self action:@selector(linkChanged:)];
        linkButton.frame={505,13,320,25};linkButton.enabled=AudioHost::linkAvailable();[setupPanel.contentView addSubview:linkButton];
        startButton=[[NSButton alloc] initWithFrame:{1040,48,188,34}]; startButton.bezelStyle=NSBezelStyleRounded; startButton.title=@"START AUDIO"; startButton.target=self; startButton.action=@selector(startAudio:); [setupPanel.contentView addSubview:startButton];
        NSButton* refresh=[[NSButton alloc] initWithFrame:{1040,90,188,27}]; refresh.bezelStyle=NSBezelStyleRounded; refresh.title=@"Refresh devices"; refresh.target=self; refresh.action=@selector(refreshClicked:); [setupPanel.contentView addSubview:refresh];
        deviceStatus=[NSTextField labelWithString:@"Audio stopped"]; deviceStatus.frame={520,92,495,34}; deviceStatus.font=[NSFont monospacedSystemFontOfSize:10 weight:NSFontWeightRegular]; deviceStatus.textColor=muted(); [setupPanel.contentView addSubview:deviceStatus];
        auto label=[&](NSString* title,NSRect rect) { NSTextField* l=[NSTextField labelWithString:title]; l.frame=rect; l.font=[NSFont systemFontOfSize:11]; l.textColor=muted(); [setupPanel.contentView addSubview:l]; };
        label(@"INPUT",{24,59,60,20}); label(@"OUTPUT",{24,97,60,20}); label(@"BUFFER",{505,59,60,20}); label(@"MIDI",{697,59,50,20});
        label(@"Physical: FLX MASTER → stereo interface input → RMX → interface output → speakers. Computer: BlackHole master input, separate physical output.",{24,145,1230,24});
        label(@"Keep headphone cueing on the FLX. Disable interface direct monitoring. Estimated latency must be confirmed with a loopback measurement.",{24,174,1230,24});
        [self refreshDevices];
        try { auto next=rmx::State::load(sessionPath());auto nextBank=rmx::makeFactoryBank();
            for(size_t i=0;i<16;++i) if(!next.samplePaths[i].empty()) { try { nextBank.slots[i]=rmx::readWav(next.samplePaths[i]); } catch(...) { message=@"A saved sample is missing. Original drum substituted; reimport the sample to restore it."; } }
            next.applySamples(nextBank);*bank=std::move(nextBank);state=std::move(next);state.apply(engine->params);for(size_t i=0;i<128;++i)host->cc[i].store(state.cc[i]);
        } catch(...) {}
        timer=[NSTimer scheduledTimerWithTimeInterval:1./30 repeats:YES block:^(NSTimer*) { [self update]; }];
    }
    return self;
}
- (void)persist {
    try { state.capture(engine->params);state.captureSamples(*bank); for(size_t i=0;i<128;++i) state.cc[i]=host->cc[i].load(); state.save(sessionPath()); } catch(const std::exception& e) { message=str(e.what()); }
}
- (void)refreshDevices {
    const auto oldInput=inputMenu.selectedItem.tag,oldOutput=outputMenu.selectedItem.tag;
    devices=AudioHost::devices(); [inputMenu removeAllItems]; [outputMenu removeAllItems];
    [inputMenu addItemWithTitle:@"No input — sampler only"]; inputMenu.lastItem.tag=0;
    if(@available(macOS 14.2,*)) { [inputMenu addItemWithTitle:@"rekordbox — direct app capture"]; inputMenu.lastItem.tag=0xfffffffe; }
    for(const auto& d:devices) { if(d.inputs>=2) { [inputMenu addItemWithTitle:str(d.name)]; inputMenu.lastItem.tag=d.id; } if(d.outputs>=2) { [outputMenu addItemWithTitle:str(d.name)]; outputMenu.lastItem.tag=d.id; } }
    if(oldInput) [inputMenu selectItemWithTag:oldInput]; [outputMenu selectItemWithTag:oldOutput?oldOutput:AudioHost::defaultOutput()];
    [self deviceChanged:nil]; sources=AudioHost::midiSources(); [midiMenu removeAllItems]; [midiMenu addItemWithTitle:@"Off — choose an FX controller"];
    for(const auto& s:sources) { [midiMenu addItemWithTitle:str(s.name)]; midiMenu.lastItem.tag=s.id; }
    host->selectMidiSource(0);
}
- (void)refreshClicked:(id)sender { (void)sender; if(!audioStarting) [self refreshDevices]; }
- (void)linkChanged:(id)sender {
    (void)sender;
    host->setLinkEnabled(linkButton.state==NSControlStateValueOn);
}
- (void)deviceChanged:(id)sender {
    (void)sender;
    auto fill=[&](NSPopUpButton* selection,NSPopUpButton* pairs,bool input) { const auto id=selection.selectedItem.tag; [pairs removeAllItems]; uint32_t channels=id==0xfffffffe?2:0; for(const auto& d:devices) if(d.id==id) channels=input?d.inputs:d.outputs; for(uint32_t i=0;i+1<channels;i+=2) { [pairs addItemWithTitle:[NSString stringWithFormat:@"Ch %u–%u",i+1,i+2]]; pairs.lastItem.tag=i; } };
    fill(inputMenu,inputPair,true); fill(outputMenu,outputPair,false);
    if(host->running()) { host->stop(); startButton.title=@"START AUDIO"; message=@"Device selection changed. Restart audio to apply."; }
}
- (void)midiChanged:(id)sender { (void)sender; host->selectMidiSource(static_cast<MIDIEndpointRef>(midiMenu.selectedItem.tag)); message=@"MIDI input selected. Right-click a knob to learn a CC. Notes 36–39 trigger drums."; }
- (void)setAudioSetupEnabled:(BOOL)enabled {
    inputMenu.enabled=enabled; outputMenu.enabled=enabled; inputPair.enabled=enabled; outputPair.enabled=enabled; bufferMenu.enabled=enabled; startButton.enabled=enabled;
}
- (void)startAudio:(id)sender {
    (void)sender; if(audioStarting) return;
    if(host->running()) {
        audioStarting=YES; [self setAudioSetupEnabled:NO]; startButton.title=@"STOPPING…";
        auto owner=hostOwner; auto audio=engineOwner; auto assets=bankOwner;
        dispatch_async(audioQueue,^{ (void)audio; (void)assets; owner->stop(); dispatch_async(dispatch_get_main_queue(),^{ self->audioStarting=NO; [self setAudioSetupEnabled:YES]; self->startButton.title=@"START AUDIO"; [self persist]; }); }); return;
    }
    const auto input=static_cast<AudioDeviceID>(inputMenu.selectedItem.tag),output=static_cast<AudioDeviceID>(outputMenu.selectedItem.tag);
    const auto inPair=static_cast<uint32_t>(inputPair.selectedItem.tag),outPair=static_cast<uint32_t>(outputPair.selectedItem.tag),frames=static_cast<uint32_t>(bufferMenu.titleOfSelectedItem.intValue);
    auto begin=^{
        if(self->audioStarting) return; self->audioStarting=YES; [self setAudioSetupEnabled:NO]; self->startButton.title=@"STARTING…";
        self->message=@"Starting audio. Allow the macOS audio-capture prompt if it appears.";
        auto owner=self->hostOwner; auto audio=self->engineOwner; auto assets=self->bankOwner;
        dispatch_async(self->audioQueue,^{
            @autoreleasepool {
                (void)audio; (void)assets; std::string error;
                const bool ok=input==0xfffffffe?owner->startRekordbox(output,outPair,frames,error):owner->start(input,output,inPair,outPair,frames,error);
                NSString* failure=str(error);
                dispatch_async(dispatch_get_main_queue(),^{ self->audioStarting=NO; [self setAudioSetupEnabled:YES]; self->startButton.title=ok?@"STOP AUDIO":@"START AUDIO"; self->message=ok?@"Audio running.":failure;
                    if(!ok) { NSAlert* alert=[NSAlert new]; alert.messageText=@"Audio route could not start"; alert.informativeText=failure; [alert runModal]; }
                });
            }
        });
    };
    if(input&&input!=0xfffffffe) [AVCaptureDevice requestAccessForMediaType:AVMediaTypeAudio completionHandler:^(BOOL granted) { dispatch_async(dispatch_get_main_queue(),^{ if(granted) begin(); else self->message=@"Audio input permission denied. Enable RMX in System Settings → Privacy & Security → Microphone."; }); }];
    else begin();
}
- (void)stopAudioForTermination {
    auto owner=hostOwner; auto audio=engineOwner; auto assets=bankOwner;
    dispatch_async(audioQueue,^{ (void)audio; (void)assets; owner->stop(); });
}
- (void)update {
    if(audioStarting) { deviceStatus.stringValue=[NSString stringWithUTF8String:host->startupStage.load()]; [self setNeedsDisplay:YES]; return; }
    if(host->deviceChanged.exchange(false)) { host->stop(); startButton.title=@"START AUDIO"; [self refreshDevices]; message=@"Audio device disconnected or its sample rate changed. Check routing and restart audio."; }
    const float cpu=host->callbackLoad.load()*100;
    deviceStatus.stringValue=host->running()?[NSString stringWithFormat:@"%.0f Hz · CPU %.1f%% · est. I/O %.1f ms\nUnder/overruns %llu/%llu · MIDI drops %llu",host->rate(),cpu,host->latencyMs.load(),host->underruns.load(),host->overruns.load(),host->midiDrops.load()]:@"Audio stopped · presets and samples remain editable";
    if(host->linkEnabled()) deviceStatus.stringValue=[deviceStatus.stringValue stringByAppendingFormat:@" · Link peers %u",host->linkPeers()];
    const int learned=host->learnedCC.exchange(-1); if(learned>=0) message=[NSString stringWithFormat:@"Learned CC %d. Move the controller through the current knob value to take over.",learned];
    [self setNeedsDisplay:YES];
}
- (void)resizeSubviewsWithOldSize:(NSSize)oldSize {
    if(oldSize.width<=0||oldSize.height<=0) return;
    for(NSView* child in self.subviews) { NSRect f=child.frame; f.origin.x*=self.bounds.size.width/oldSize.width; f.size.width*=self.bounds.size.width/oldSize.width; f.origin.y*=self.bounds.size.height/oldSize.height; f.size.height*=self.bounds.size.height/oldSize.height; child.frame=f; }
}
- (void)audioSetup:(id)sender {
    (void)sender; [setupPanel center]; [setupPanel makeKeyAndOrderFront:nil];
}
- (void)drawRect:(NSRect)dirty {
    (void)dirty; [NSColor.blackColor setFill]; NSRectFill(self.bounds);
    [NSGraphicsContext saveGraphicsState]; NSAffineTransform* scale=[NSAffineTransform transform]; [scale scaleXBy:self.bounds.size.width/2048 yBy:self.bounds.size.height/921]; [scale concat];
    [panelImage drawInRect:{0,0,2048,921} fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1 respectFlipped:YES hints:@{NSImageHintInterpolation:@(NSImageInterpolationHigh)}];
    for(const auto& c:controls) {
        if(c.kind==Kind::Knob&&c.param!=Param::Tempo) {
            const auto& info=rmx::parameters[static_cast<size_t>(c.param)]; const float v=engine->params.get(c.param);
            const float angle=(v-info.initial)/(info.max-info.min)*270;
            if(std::abs(angle)>.05f) {
                [NSGraphicsContext saveGraphicsState]; [[NSBezierPath bezierPathWithOvalInRect:c.rect] addClip];
                NSAffineTransform* rotate=[NSAffineTransform transform]; [rotate translateXBy:NSMidX(c.rect) yBy:NSMidY(c.rect)]; [rotate rotateByDegrees:angle]; [rotate translateXBy:-NSMidX(c.rect) yBy:-NSMidY(c.rect)]; [rotate concat];
                [panelImage drawInRect:{0,0,2048,921} fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1 respectFlipped:YES hints:@{NSImageHintInterpolation:@(NSImageInterpolationHigh)}]; [NSGraphicsContext restoreGraphicsState];
            }
        }
        if(c.action==8) { const int source=static_cast<int>(engine->params.get(Param::SceneSource)); const bool on=source==2||source==static_cast<int>(c.value); if(!on) box(NSInsetRect(c.rect,3,3),color(0,0,0,.65),4); }
        if(c.kind==Kind::Toggle||c.kind==Kind::Choice||c.kind==Kind::Pad) {
            const float v=engine->params.get(c.param); const bool on=c.kind==Kind::Toggle?v>.5f:c.kind==Kind::Choice?std::abs(v-c.value)<.01f:selectedPad==static_cast<int>(c.value);
            if(!on) box(NSInsetRect(c.rect,3,3),color(0,0,0,.30),5);
            else if(c.param!=Param::IsolateMode) { [NSGraphicsContext saveGraphicsState]; NSShadow* glow=[NSShadow new]; glow.shadowColor=[(c.param==Param::Quantize||c.param==Param::AutoTempo)?NSColor.redColor:color(.65,1,.1) colorWithAlphaComponent:.7]; glow.shadowBlurRadius=11; [glow set]; NSBezierPath* border=[NSBezierPath bezierPathWithRoundedRect:NSInsetRect(c.rect,3,3) xRadius:5 yRadius:5]; [[glow.shadowColor colorWithAlphaComponent:.35] setStroke]; border.lineWidth=2; [border stroke]; [NSGraphicsContext restoreGraphicsState]; }
        }
    }
    if(engine->params.get(Param::AutoTempo)>.5f&&engine->meters.confidence.load()<.2f) {
        const float alpha=static_cast<float>(.25+.22*std::sin(NSDate.timeIntervalSinceReferenceDate*5)); box({1101,108,80,39},color(0,0,0,alpha),3);
    }
    // Selected annular button lights independently of the static panel artwork.
    if(engine->params.get(Param::SceneOn)>.5f) {
        const int selected=static_cast<int>(engine->params.get(Param::SceneType)); const CGFloat begin=selected<5?-153+selected*25.2:127.8-(selected-5)*25.2;
        NSBezierPath* wedge=[NSBezierPath bezierPath]; const CGFloat end=begin+25.2; const CGFloat rad=begin*3.141592653589793/180;
        [wedge moveToPoint:{1503+194*std::cos(rad),466+194*std::sin(rad)}]; [wedge appendBezierPathWithArcWithCenter:{1503,466} radius:316 startAngle:begin endAngle:end clockwise:NO]; [wedge appendBezierPathWithArcWithCenter:{1503,466} radius:194 startAngle:end endAngle:begin clockwise:YES]; [wedge closePath]; [(selected<5?color(1,.65,.15,.14):color(.05,.8,.8,.2)) setFill]; [wedge fill];
    }
    auto meter=[&](bool output,float peak) {
        auto r=rmx::panel::meterRect(output); box({r.x,r.y,r.w,r.h},color(.018,.021,.019),0);
        const float db=20*std::log10(std::max(peak,1e-7f));
        for(int group=0;group<11;++group) for(int led=0;led<3;++led) for(int row=0;row<2;++row) { const float threshold=-30+group*3.f; const bool lit=db>=threshold; NSColor* ledColor=group==10?color(1,.05,.02):group>6?color(.95,.85,.15):color(.7,.92,.24); box({r.x+group*33.5+led*7.8,r.y+row*8,5.5,5.5},lit?ledColor:[ledColor colorWithAlphaComponent:.12],.4); }
    };
    meter(false,engine->meters.input.load()); meter(true,engine->meters.output.load());
    box({924,146,121,66},color(.015,.012,.012),0);
    const int tempo=std::clamp(static_cast<int>(std::round(host->running()?engine->meters.tempo.load():engine->params.get(Param::Tempo))),0,999);
    const std::array<int,10> segments{0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
    for(int digit=0;digit<3;++digit) { const int number=digit==0?tempo/100:digit==1?(tempo/10)%10:tempo%10; const CGFloat x=934+digit*36,y=156; const NSPoint lines[7][2]={{{x+5,y},{x+25,y}},{{x+27,y+3},{x+25,y+22}},{{x+24,y+27},{x+22,y+46}},{{x+1,y+49},{x+20,y+49}},{{x-1,y+27},{x-3,y+46}},{{x+2,y+3},{x,y+22}},{{x+2,y+24},{x+23,y+24}}};
        for(int i=0;i<7;++i) { NSBezierPath* line=[NSBezierPath bezierPath]; [line moveToPoint:lines[static_cast<size_t>(i)][0]]; [line lineToPoint:lines[static_cast<size_t>(i)][1]]; [(segments[static_cast<size_t>(number)]&(1<<i)?color(.95,.55,.12):color(.11,.05,.01)) setStroke]; line.lineWidth=5; [line stroke]; }
    }
    // Bank indicators and the touch-strip light follow the actual engine state.
    const int currentBank=static_cast<int>(engine->params.get(Param::Bank));
    for(int i=0;i<4;++i) if(engine->params.get(Param::SampleSource)<.5f||i!=currentBank) box({488.+i*115,590,30,23},color(0,0,0,.6),3);
    const auto stripValues=engine->params.snapshot();
    for(unsigned position=0;position<8;++position) {
        box({475.+position*51,773,47,24},color(.025,.028,.032),3);
        text(str(rmx::xPadBeatNames[rmx::xPadBeatChoice(stripValues,static_cast<float>(position))]),{475.+position*51,775,47,20},14,cyan(),true,NSTextAlignmentCenter);
    }
    if(dragging>=0&&controls[static_cast<size_t>(dragging)].kind==Kind::Strip) { const int division=static_cast<int>(engine->params.get(Param::XRoll)); box({475.+division*51,742,47,76},color(.55,.73,1,.22),4); }
    const float lever=engine->params.get(Param::ReleaseAmount);
    if(lever>.005f) { box({1884,430,113,105},color(.015,.015,.015),4); NSGradient* gradient=[[NSGradient alloc] initWithStartingColor:color(.25,.25,.25) endingColor:color(.045,.045,.045)]; NSBezierPath* handle=[NSBezierPath bezierPathWithRoundedRect:{1891,435+lever*62,99,30} xRadius:10 yRadius:10]; [gradient drawInBezierPath:handle angle:90]; }
    const int releaseType=static_cast<int>(engine->params.get(Param::ReleaseType)); box({1903,301,61,47},color(.025,.025,.025),4); box({1908+(2-releaseType)*17.,307,15,34},color(.18,.18,.18),2);
    box({1831,151,69,43},color(.025,.025,.025),3); box({1836+engine->params.get(Param::UserSettings)*29,156,29,33},color(.18,.18,.18),2);
    box({1690,50,295,63},color(.025,.025,.025),8);
    text(@"RMX",{1748,52,220,56},46,color(.85,.87,.87),true,NSTextAlignmentRight);
    box({1828,578,185,76},color(.035,.035,.035),3);
    text(@"PERFORMANCE FX",{1836,584,167,21},16,color(.7,.73,.74),true);
    text(@"RMX",{1834,608,169,43},34,color(.9,.92,.92),true);
    [NSGraphicsContext restoreGraphicsState];
}
- (NSPoint)surfacePoint:(NSEvent*)event {
    NSPoint p=[self convertPoint:event.locationInWindow fromView:nil]; p.x*=2048/self.bounds.size.width; p.y*=921/self.bounds.size.height; return p;
}
- (void)change:(Param)p value:(float)v {
    engine->params.set(p,v); const auto& info=rmx::parameters[static_cast<size_t>(p)]; host->sendFeedback(p,(engine->params.get(p)-info.min)/(info.max-info.min));
}
- (void)mouseDown:(NSEvent*)event {
    [self.window makeFirstResponder:self]; const NSPoint point=[self surfacePoint:event]; dragging=-1;
    const int scene=rmx::panel::sceneAt(static_cast<float>(point.x),static_cast<float>(point.y));
    if(scene>=0) { const bool wasOn=engine->params.get(Param::SceneOn)>.5f&&static_cast<int>(engine->params.get(Param::SceneType))==scene; [self change:Param::SceneType value:static_cast<float>(scene)]; [self change:Param::SceneOn value:wasOn?0:1]; return; }
    for(size_t i=0;i<controls.size();++i) {
        auto& c=controls[i]; if(!NSPointInRect(point,c.rect)) continue;
        if(c.kind==Kind::Pad) selectedPad=static_cast<int>(c.value);
        if(c.action==7) { dragging=static_cast<int>(i); [self sendEvent:rmx::Event{rmx::EventType::NudgeStart,0,c.value}]; return; }
        rmx::panel::Control model{{static_cast<float>(c.rect.origin.x),static_cast<float>(c.rect.origin.y),static_cast<float>(c.rect.size.width),static_cast<float>(c.rect.size.height)},c.kind,c.param,c.label,c.value,c.action};
        const bool handled=rmx::panel::activate(model,[&](Param p){ return engine->params.get(p); },[&](Param p,float v){ [self change:p value:v]; },[&](rmx::Event e){ [self sendEvent:e]; },event.modifierFlags&NSEventModifierFlagShift,event.modifierFlags&NSEventModifierFlagOption);
        if(handled) { [self setNeedsDisplay:YES]; return; }
        if(c.kind==Kind::Action) { if(c.action==1) [self settings:nil]; }
        else if(c.kind==Kind::Knob&&event.clickCount==2) { [self editNumeric:c.param]; }
        else {
            dragging=static_cast<int>(i); dragOrigin=point; dragStart=engine->params.get(c.param);
            if(c.kind==Kind::Lever) [self change:c.param value:std::clamp(static_cast<float>((point.y-c.rect.origin.y)/c.rect.size.height),0.f,1.f)];
            if(c.kind==Kind::Strip) { [self change:c.param value:std::clamp(static_cast<float>((point.x-c.rect.origin.x)/c.rect.size.width*8),0.f,7.f)]; engine->enqueue({rmx::EventType::RollStart,static_cast<uint8_t>(selectedPad)}); }
        }
        [self setNeedsDisplay:YES]; break;
    }
}
- (void)mouseDragged:(NSEvent*)event {
    if(dragging<0) return; auto& c=controls[static_cast<size_t>(dragging)]; const NSPoint point=[self surfacePoint:event]; const auto& info=rmx::parameters[static_cast<size_t>(c.param)];
    if(c.kind==Kind::Knob) { const float fine=(event.modifierFlags&NSEventModifierFlagShift)?.12f:1.f; [self change:c.param value:dragStart+static_cast<float>(dragOrigin.y-point.y)*(info.max-info.min)/250*fine]; if(c.param==Param::SceneDepth) [self change:Param::SceneOn value:1]; }
    else if(c.kind==Kind::Lever) [self change:c.param value:std::clamp(static_cast<float>((point.y-c.rect.origin.y)/c.rect.size.height),0.f,1.f)];
    else if(c.kind==Kind::Strip) [self change:c.param value:std::clamp(static_cast<float>((point.x-c.rect.origin.x)/c.rect.size.width*8),0.f,7.f)];
    [self setNeedsDisplay:YES];
}
- (void)mouseUp:(NSEvent*)event {
    (void)event; if(dragging>=0) { auto& c=controls[static_cast<size_t>(dragging)]; if(c.action==7) [self sendEvent:rmx::Event{rmx::EventType::NudgeStop}]; if(c.kind==Kind::Lever) [self change:c.param value:0]; if(c.kind==Kind::Strip) engine->enqueue({rmx::EventType::RollStop}); } dragging=-1;
}
- (void)scrollWheel:(NSEvent*)event {
    const NSPoint point=[self surfacePoint:event];
    for(const auto& c:controls) if(c.kind==Kind::Knob&&NSPointInRect(point,c.rect)) { const auto& info=rmx::parameters[static_cast<size_t>(c.param)]; [self change:c.param value:engine->params.get(c.param)+static_cast<float>(event.scrollingDeltaY)*(info.max-info.min)/300]; break; }
}
- (void)rightMouseDown:(NSEvent*)event {
    const NSPoint point=[self surfacePoint:event];
    for(const auto& c:controls) if(c.param!=Param::Count&&NSPointInRect(point,c.rect)) { editSlot=static_cast<int>(c.param); NSMenu* menu=[NSMenu new]; [menu addItemWithTitle:@"Enter value…" action:@selector(numericMenu:) keyEquivalent:@""].target=self; [menu addItemWithTitle:@"Reset to default" action:@selector(resetMenu:) keyEquivalent:@""].target=self; [menu addItemWithTitle:@"Learn next MIDI CC" action:@selector(learnMenu:) keyEquivalent:@""].target=self; [NSMenu popUpContextMenu:menu withEvent:event forView:self]; break; }
}
- (void)numericMenu:(id)sender { (void)sender; [self editNumeric:static_cast<Param>(editSlot)]; }
- (void)resetMenu:(id)sender { (void)sender; [self change:static_cast<Param>(editSlot) value:rmx::parameters[static_cast<size_t>(editSlot)].initial]; }
- (void)learnMenu:(id)sender { (void)sender; host->learnTarget.store(editSlot); message=@"Move a CC on your selected MIDI device. Audio must be running to receive controls."; }
- (void)editNumeric:(Param)p {
    const auto& info=rmx::parameters[static_cast<size_t>(p)]; NSAlert* alert=[NSAlert new]; alert.messageText=str(info.name); alert.informativeText=[NSString stringWithFormat:@"Range %.3g to %.3g",info.min,info.max];
    NSTextField* field=[[NSTextField alloc] initWithFrame:{0,0,240,25}]; field.stringValue=[NSString stringWithFormat:@"%.4g",engine->params.get(p)]; alert.accessoryView=field; [alert addButtonWithTitle:@"Apply"]; [alert addButtonWithTitle:@"Cancel"];
    if([alert runModal]==NSAlertFirstButtonReturn) { NSScanner* scanner=[NSScanner scannerWithString:field.stringValue]; float value; if([scanner scanFloat:&value]&&scanner.isAtEnd&&std::isfinite(value)) [self change:p value:value]; else message=@"Enter a finite numeric value."; }
}
- (void)keyDown:(NSEvent*)event {
    NSString* key=event.charactersIgnoringModifiers.lowercaseString;
    if([key isEqualToString:@" "]) [self change:Param::Bypass value:1-engine->params.get(Param::Bypass)];
    else if([key isEqualToString:@"t"]) [self sendEvent:rmx::Event{rmx::EventType::Tap}];
    else if(event.keyCode==53) [self sendEvent:rmx::Event{rmx::EventType::Panic}];
    else if(key.length==1&&[key characterAtIndex:0]>='1'&&[key characterAtIndex:0]<='4') { selectedPad=[key characterAtIndex:0]-'1'; if(!event.isARepeat) engine->enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(selectedPad)}); }
    else [super keyDown:event];
}
- (void)savePreset:(id)sender {
    (void)sender; NSSavePanel* panel=[NSSavePanel savePanel]; panel.nameFieldStringValue=@"Performance.rmx";
    if([panel runModal]==NSModalResponseOK) { try { state.capture(engine->params);state.captureSamples(*bank); for(size_t i=0;i<128;++i) state.cc[i]=host->cc[i].load(); state.save(panel.URL.fileSystemRepresentation); message=@"Preset saved with sample references and MIDI mappings."; } catch(const std::exception& e) { message=str(e.what()); } }
}
- (void)loadPreset:(id)sender {
    (void)sender; if(audioStarting) return; NSOpenPanel* panel=[NSOpenPanel openPanel]; panel.allowsMultipleSelection=NO; panel.canChooseDirectories=NO;
    if([panel runModal]!=NSModalResponseOK) return;
    try {
        auto next=rmx::State::load(panel.URL.fileSystemRepresentation); auto newBank=rmx::makeFactoryBank(); std::string missing;
        for(size_t i=0;i<16;++i) if(!next.samplePaths[i].empty()) { try { newBank.slots[i]=rmx::readWav(next.samplePaths[i]); } catch(const std::exception&) { missing+=" "+std::to_string(i+1); } }
        next.applySamples(newBank);
        const bool restart=host->running(); host->stop(); *bank=std::move(newBank); state=std::move(next); state.apply(engine->params); for(size_t i=0;i<128;++i) host->cc[i].store(state.cc[i]);
        if(restart) [self startAudio:nil];
        message=missing.empty()?@"Preset restored.":str("Missing samples in slots"+missing+". Factory sounds substituted.");
    } catch(const std::exception& e) { message=str(e.what()); }
}
- (void)importSample:(id)sender {
    (void)sender; if(audioStarting) return; NSOpenPanel* panel=[NSOpenPanel openPanel]; panel.allowedContentTypes=@[UTTypeWAV]; panel.allowsMultipleSelection=NO; panel.canChooseDirectories=NO;
    panel.message=[NSString stringWithFormat:@"Import into bank %d, %@. Each bank holds at most 16 seconds total.",static_cast<int>(engine->params.get(Param::Bank))+1,str(rmx::drumNames[static_cast<size_t>(selectedPad)])];
    if([panel runModal]!=NSModalResponseOK) return;
    try { auto sample=rmx::readWav(panel.URL.fileSystemRepresentation); const size_t slot=static_cast<size_t>(engine->params.get(Param::Bank))*4+selectedPad; if(!rmx::sampleFitsBank(*bank,slot,sample))throw std::runtime_error("Sample would exceed this bank's 16-second total"); const bool restart=host->running(); host->stop(); bank->slots[slot]=std::move(sample);engine->params.set(Param::SampleSource,1); state.samplePaths[slot]=panel.URL.fileSystemRepresentation; if(restart) [self startAudio:nil]; [self persist]; message=@"Sample imported. Audio was briefly suspended to install the new asset safely."; }
    catch(const std::exception& e) { message=str(e.what()); }
}
- (void)editSample:(id)sender {
    (void)sender; if(audioStarting) return; const size_t slot=static_cast<size_t>(engine->params.get(Param::Bank))*4+selectedPad;
    const auto& original=bank->slots[slot]; if(original.frames.empty()) return;
    const double duration=original.frames.size()/original.rate;
    NSAlert* dialog=[NSAlert new]; dialog.messageText=@"Edit selected sample";
    dialog.informativeText=[NSString stringWithFormat:@"Bank %d · %@ · %.3f seconds. Edits create a new managed WAV.",static_cast<int>(slot/4)+1,str(rmx::drumNames[slot%4]),duration];
    NSView* form=[[NSView alloc] initWithFrame:{0,0,400,230}];
    NSTextField* begin=[[NSTextField alloc] initWithFrame:{200,192,150,24}]; begin.stringValue=@"0";
    NSTextField* end=[[NSTextField alloc] initWithFrame:{200,158,150,24}]; end.stringValue=[NSString stringWithFormat:@"%.6f",duration];
    for(int i=0;i<2;++i) { NSTextField* label=[NSTextField labelWithString:i?@"End (seconds)":@"Start (seconds)"]; label.frame={0,192.-i*34,190,24}; [form addSubview:label]; }
    [form addSubview:begin]; [form addSubview:end];
    NSButton* loop=[NSButton checkboxWithTitle:@"Loop (slot 1 only)" target:nil action:nil];loop.frame={0,112,380,25};loop.enabled=slot%4==0;loop.state=original.playback.loop?NSControlStateValueOn:NSControlStateValueOff;[form addSubview:loop];
    NSTextField* bpm=[[NSTextField alloc] initWithFrame:{200,78,150,24}];bpm.stringValue=[NSString stringWithFormat:@"%.3f",original.playback.bpm];[form addSubview:bpm];
    NSTextField* bpmLabel=[NSTextField labelWithString:@"Sample BPM (70–200)"];bpmLabel.frame={0,78,190,24};[form addSubview:bpmLabel];
    NSButton* normalize=[NSButton checkboxWithTitle:@"Normalize peak to −0.45 dBFS" target:nil action:nil]; normalize.frame={0,40,380,25}; [form addSubview:normalize];
    NSButton* reverse=[NSButton checkboxWithTitle:@"Reverse" target:nil action:nil]; reverse.frame={0,5,380,25}; [form addSubview:reverse];
    dialog.accessoryView=form; [dialog addButtonWithTitle:@"Apply"]; [dialog addButtonWithTitle:@"Cancel"];
    if([dialog runModal]!=NSAlertFirstButtonReturn) return;
    double sampleBpm=0;NSScanner* scanner=[NSScanner scannerWithString:bpm.stringValue];
    if(![scanner scanDouble:&sampleBpm]||!scanner.isAtEnd||!rmx::validSamplePlayback(slot,{sampleBpm,loop.state==NSControlStateValueOn})) {message=@"Use sample BPM 70–200. Loop mode is available only in slot 1.";return;}
    const double a=begin.doubleValue,b=end.doubleValue;
    if(!std::isfinite(a)||!std::isfinite(b)||a<0||b>duration+.000001||b<=a||b-a<.001) { message=@"Invalid trim. Use a start before the end, inside the sample."; return; }
    try {
        rmx::Sample edited; edited.rate=original.rate;edited.playback={sampleBpm,loop.state==NSControlStateValueOn};
        const size_t first=static_cast<size_t>(a*original.rate),last=std::min(original.frames.size(),static_cast<size_t>(std::round(b*original.rate)));
        edited.frames.assign(original.frames.begin()+static_cast<std::ptrdiff_t>(first),original.frames.begin()+static_cast<std::ptrdiff_t>(last));
        if(reverse.state==NSControlStateValueOn) std::reverse(edited.frames.begin(),edited.frames.end());
        if(normalize.state==NSControlStateValueOn) { float peak=0; for(auto x:edited.frames) peak=std::max({peak,std::abs(x.l),std::abs(x.r)}); if(peak>1.e-8f) for(auto& x:edited.frames) x=x*(.95f/peak); }
        if(!rmx::sampleFitsBank(*bank,slot,edited))throw std::runtime_error("Sample would exceed this bank's 16-second total");
        const auto folder=sessionPath().parent_path()/"Samples"; std::filesystem::create_directories(folder);
        const auto file=folder/("slot-"+std::to_string(slot)+"-"+std::to_string(static_cast<uint64_t>(NSDate.timeIntervalSinceReferenceDate*1000))+".wav"); rmx::writeWav(file,edited);
        const bool restart=host->running(); host->stop(); bank->slots[slot]=std::move(edited);engine->params.set(Param::SampleSource,1); state.samplePaths[slot]=file.string(); if(restart) [self startAudio:nil]; [self persist]; message=@"Edited sample saved and installed.";
    } catch(const std::exception& e) { message=str(e.what()); }
}
- (void)settings:(id)sender {
    (void)sender;
    NSAlert* dialog=[NSAlert new]; dialog.messageText=@"User settings";
    dialog.informativeText=@"Choose effect ranges, patterns and release behavior. Apply selects User; the Default switch restores factory behavior without deleting your choices.";
    std::vector<Param> editable{Param::InputGain,Param::OutputGain,Param::SampleSource};
    for(size_t i=0;i<rmx::parameterCount;++i) if(rmx::parameters[i].advanced) editable.push_back(static_cast<Param>(i));
    const CGFloat contentHeight=editable.size()*32+16;
    NSView* form=[[NSView alloc] initWithFrame:{0,0,540,440}];
    NSScrollView* scroll=[[NSScrollView alloc] initWithFrame:{0,45,540,395}]; scroll.hasVerticalScroller=YES; scroll.borderType=NSBezelBorder;
    NSView* document=[[NSView alloc] initWithFrame:{0,0,520,contentHeight}]; scroll.documentView=document; [form addSubview:scroll];
    NSMutableArray<NSControl*>* fields=[NSMutableArray array];
    for(size_t i=0;i<editable.size();++i) {
        const Param p=editable[i];const auto& info=rmx::parameters[static_cast<size_t>(p)];const CGFloat y=contentHeight-32-i*32;
        NSTextField* label=[NSTextField labelWithString:str(info.name)]; label.frame={8,y,310,24};[document addSubview:label];
        const auto choices=rmx::parameterChoices(p);
        if(!choices.empty()) {
            NSPopUpButton* choice=[[NSPopUpButton alloc] initWithFrame:{330,y,165,26} pullsDown:NO];
            for(auto title:choices) [choice addItemWithTitle:str(title)];
            [choice selectItemAtIndex:static_cast<NSInteger>(engine->params.get(p))]; [document addSubview:choice];[fields addObject:choice];
        } else {
            NSTextField* field=[[NSTextField alloc] initWithFrame:{330,y,165,24}]; field.stringValue=[NSString stringWithFormat:@"%.4g",engine->params.get(p)];[document addSubview:field];[fields addObject:field];
        }
    }
    NSButton* wet=[NSButton checkboxWithTitle:@"Wet only for parallel mixer send/return" target:nil action:nil];wet.frame={0,10,530,24};wet.state=engine->params.get(Param::WetOnly)>.5f?NSControlStateValueOn:NSControlStateValueOff;[form addSubview:wet];
    [document scrollPoint:NSMakePoint(0,std::max(CGFloat(0),contentHeight-395))];
    dialog.accessoryView=form;[dialog addButtonWithTitle:@"Apply"];[dialog addButtonWithTitle:@"Routing guide"];[dialog addButtonWithTitle:@"Cancel"];
    const auto result=[dialog runModal];
    if(result==NSAlertFirstButtonReturn) {
        std::vector<float> values; values.reserve(editable.size());
        for(size_t i=0;i<editable.size();++i) {
            float value=0;NSControl* control=fields[i];
            if([control isKindOfClass:NSPopUpButton.class]) value=static_cast<float>(((NSPopUpButton*)control).indexOfSelectedItem);
            else {
                NSScanner* scanner=[NSScanner scannerWithString:((NSTextField*)control).stringValue];
                if(![scanner scanFloat:&value]||!scanner.isAtEnd||!std::isfinite(value)) {message=@"Enter finite numeric values. No settings were changed.";return;}
            }
            const auto& info=rmx::parameters[static_cast<size_t>(editable[i])];
            if(value<info.min||value>info.max) {message=[NSString stringWithFormat:@"%@ must be between %.3g and %.3g. No settings were changed.",str(info.name),info.min,info.max];return;}
            values.push_back(value);
        }
        for(size_t i=0;i<editable.size();++i) engine->params.set(editable[i],values[i]);
        engine->params.set(Param::UserSettings,1);engine->params.set(Param::WetOnly,wet.state==NSControlStateValueOn?1:0);[self persist];
    } else if(result==NSAlertSecondButtonReturn) [self routingGuide:nil];
}
- (void)routingGuide:(id)sender {
    (void)sender; NSAlert* dialog=[NSAlert new]; dialog.messageText=@"FLX4 / FLX6 live audio routing";
    dialog.informativeText=@"PHYSICAL\nController MASTER RCA → interface stereo LINE IN → RMX → interface LINE OUT → speakers. Keep headphones in the controller. Disable interface direct monitoring. Wet only must be OFF.\n\nCOMPUTER\nCreate a Core Audio aggregate device with BlackHole 2ch and the FLX. Select it in rekordbox: master to BlackHole, headphones to FLX headphone channels. In RMX: input BlackHole, output your speakers/interface. Use a consistent sample rate and drift correction for secondary devices. The app must never output back into BlackHole.\n\nBoth computer routing and latency must be checked on your specific controller before a set. The displayed I/O latency is an estimate, not a physical loopback measurement. Software bypass cannot keep audio flowing if the app or computer stops.";
    [dialog runModal];
}
@end

@interface AppDelegate : NSObject<NSApplicationDelegate,NSWindowDelegate> {
    std::shared_ptr<rmx::Engine> engine;
    std::shared_ptr<rmx::SampleBank> samples;
    std::shared_ptr<AudioHost> host;
    NSWindow* window;
    Surface* surface;
}
@end
@implementation AppDelegate
- (void)applicationDidFinishLaunching:(NSNotification*)notification {
    (void)notification; engine=std::make_shared<rmx::Engine>(); samples=std::make_shared<rmx::SampleBank>(rmx::makeFactoryBank()); engine->setBank(samples.get()); engine->prepare(48000,8192); host=std::make_shared<AudioHost>(*engine);
    window=[[NSWindow alloc] initWithContentRect:{0,0,1280,575.625} styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable|NSWindowStyleMaskResizable backing:NSBackingStoreBuffered defer:NO]; window.title=@"RMX — Remix Station"; window.minSize={960,454}; window.contentAspectRatio={2048,921}; window.delegate=self; window.backgroundColor=color(.035,.043,.055); window.appearance=[NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
    surface=[[Surface alloc] initWithEngine:engine host:host bank:samples]; surface.autoresizingMask=NSViewWidthSizable|NSViewHeightSizable; window.contentView=surface;
    NSMenu* bar=[NSMenu new]; NSMenuItem* appItem=[NSMenuItem new]; [bar addItem:appItem]; NSMenu* app=[NSMenu new]; [app addItemWithTitle:@"About RMX" action:@selector(orderFrontStandardAboutPanel:) keyEquivalent:@""]; [app addItem:NSMenuItem.separatorItem]; [app addItemWithTitle:@"Quit RMX" action:@selector(terminate:) keyEquivalent:@"q"]; appItem.submenu=app;
    NSMenuItem* fileItem=[NSMenuItem new]; [bar addItem:fileItem]; NSMenu* file=[[NSMenu alloc] initWithTitle:@"File"]; [file addItemWithTitle:@"Load preset…" action:@selector(loadPreset:) keyEquivalent:@"o"].target=surface; [file addItemWithTitle:@"Save preset…" action:@selector(savePreset:) keyEquivalent:@"s"].target=surface; [file addItemWithTitle:@"Import sample…" action:@selector(importSample:) keyEquivalent:@"i"].target=surface; [file addItemWithTitle:@"Edit selected sample…" action:@selector(editSample:) keyEquivalent:@"e"].target=surface;
    [file addItemWithTitle:@"Audio & MIDI setup…" action:@selector(audioSetup:) keyEquivalent:@","].target=surface;
    [file addItemWithTitle:@"Engine settings…" action:@selector(settings:) keyEquivalent:@""].target=surface;
    [file addItemWithTitle:@"Routing guide" action:@selector(routingGuide:) keyEquivalent:@""].target=surface;
    fileItem.submenu=file; NSApp.mainMenu=bar;
    NSArray<NSString*>* args=NSProcessInfo.processInfo.arguments;
    if(args.count==3&&[args[1] isEqualToString:@"--snapshot"]) {
        NSBitmapImageRep* bitmap=[surface bitmapImageRepForCachingDisplayInRect:surface.bounds]; [surface cacheDisplayInRect:surface.bounds toBitmapImageRep:bitmap]; [[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:args[2] atomically:YES]; [NSApp terminate:nil]; return;
    }
    const NSRect screen=NSScreen.mainScreen.visibleFrame; const CGFloat scale=std::min({1.,screen.size.width/1340,(screen.size.height-45)/575.625}); [window setContentSize:{1280*scale,575.625*scale}]; window.minSize={960,454};
    [window center]; [window makeKeyAndOrderFront:nil]; [window makeFirstResponder:surface]; [NSApp activateIgnoringOtherApps:YES];
}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication*)sender { (void)sender; return YES; }
- (void)applicationWillTerminate:(NSNotification*)notification { (void)notification; [surface persist]; [surface stopAudioForTermination]; [surface->timer invalidate]; }
- (void)windowDidResignKey:(NSNotification*)notification { (void)notification; if(surface->dragging>=0) { const auto& c=surface->controls[static_cast<size_t>(surface->dragging)]; if(c.kind==Kind::Lever) engine->params.set(Param::ReleaseAmount,0); if(c.kind==Kind::Strip) engine->enqueue({rmx::EventType::RollStop}); surface->dragging=-1; } }
@end
int main(int argc,const char* argv[]) {
    (void)argc; (void)argv; @autoreleasepool { NSApplication* app=[NSApplication sharedApplication]; app.activationPolicy=NSApplicationActivationPolicyRegular; AppDelegate* delegate=[AppDelegate new]; app.delegate=delegate; [app run]; } return 0;
}
