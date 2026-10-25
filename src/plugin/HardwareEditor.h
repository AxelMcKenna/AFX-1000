#pragma once
#include "rmx/Panel.h"
#include "rmx/Skin.h"
#include "rmx/PanelController.h"
#include "BinaryData.h"

class RMXEditor final : public juce::AudioProcessorEditor,private juce::Timer {
    RMXProcessor& processor;
    std::vector<rmx::panel::Control> controls=rmx::panel::controls();
    juce::Image skin;
    std::unique_ptr<juce::FileChooser> chooser;
    int selectedPad{},dragging{-1};
    float dragValue{};
    juce::Point<float> dragOrigin;
    using Param=rmx::Param;
    using Kind=rmx::panel::Kind;
public:
    explicit RMXEditor(RMXProcessor& p):AudioProcessorEditor(p),processor(p) {
        static const juce::Image cached=[] {
            return juce::ImageFileFormat::loadFrom(BinaryData::panel_png,BinaryData::panel_pngSize);
        }();
        skin=cached; setResizable(true,true); setResizeLimits(900,405,2048,921); getConstrainer()->setFixedAspectRatio(2048./921); setSize(1280,576); setWantsKeyboardFocus(true); startTimerHz(30);
    }
    ~RMXEditor() override { stopTimer(); if(dragging>=0) finishGesture(); }
    void paint(juce::Graphics& g) override {
        g.fillAll(juce::Colours::black); g.addTransform(juce::AffineTransform::scale(getWidth()/2048.f,getHeight()/921.f));
        g.drawImage(skin,juce::Rectangle<float>(0,0,2048,921));
        for(const auto& c:controls) {
            auto r=rect(c.rect);
            if(c.kind==Kind::Knob&&c.param!=Param::Tempo) {
                const auto& info=rmx::parameters[static_cast<size_t>(c.param)];const float angle=(-225+270*(value(c.param)-info.min)/(info.max-info.min))*juce::MathConstants<float>::pi/180;
                const float radius=r.getWidth()/2,x=r.getCentreX(),y=r.getCentreY();
                g.setColour(juce::Colour(0xffeff5e3));g.drawLine(x+radius*.48f*std::cos(angle),y+radius*.48f*std::sin(angle),x+radius*.80f*std::cos(angle),y+radius*.80f*std::sin(angle),radius>60?5.f:3.5f);
            }
            if(c.action==8) { const int source=static_cast<int>(value(Param::SceneSource)); const bool on=source==2||source==static_cast<int>(c.value); if(!on) { g.setColour(juce::Colours::black.withAlpha(.65f)); g.fillRoundedRectangle(r.reduced(3),4); } }
            if((c.kind==Kind::Toggle||c.kind==Kind::Choice||c.kind==Kind::Pad)&&c.param!=Param::UserSettings) {
                const bool on=(c.param!=Param::IsolateMode||value(Param::IsolateOn)>.5f)&&(c.kind==Kind::Toggle?value(c.param)>.5f:c.kind==Kind::Choice?std::abs(value(c.param)-c.value)<.01f:selectedPad==static_cast<int>(c.value));
                const juce::Rectangle<float> lamp{r.getX()+8,r.getBottom()-9,r.getWidth()-16,3};
                g.setColour(on?(c.param==Param::Quantize||c.param==Param::AutoTempo?juce::Colour(0xffffa83d):juce::Colour(0xff59efc2)):juce::Colour(0xff13251e));g.fillRoundedRectangle(lamp,1);
            }
        }
        if(value(Param::SceneOn)>.5f) {
            const int scene=static_cast<int>(value(Param::SceneType)); const float begin=(scene<5?-153+scene*25.2f:127.8f-(scene-5)*25.2f)*juce::MathConstants<float>::pi/180;
            juce::Path wedge; wedge.addCentredArc(1503,466,316,316,0,begin+juce::MathConstants<float>::halfPi,begin+juce::MathConstants<float>::halfPi+juce::MathConstants<float>::pi*25.2f/180,true);
            wedge.addCentredArc(1503,466,194,194,0,begin+juce::MathConstants<float>::halfPi+juce::MathConstants<float>::pi*25.2f/180,begin+juce::MathConstants<float>::halfPi,false); wedge.closeSubPath();
            g.setColour((scene<5?juce::Colour(0xffffb041):juce::Colour(0xff22d3c4)).withAlpha(.16f)); g.fillPath(wedge);
        }
        for(int output=0;output<2;++output) {
            auto r=rmx::panel::meterRect(output!=0); g.setColour(juce::Colour(0xff060706)); g.fillRect(rect(r));
            float db=20*std::log10(std::max(output?processor.engine.meters.output.load():processor.engine.meters.input.load(),1.e-7f));
            for(int group=0;group<11;++group) for(int led=0;led<3;++led) for(int row=0;row<2;++row) { auto color=group==10?juce::Colour(0xffff2718):group>6?juce::Colour(0xffe8c92e):juce::Colour(0xff40d9b1); g.setColour(color.withAlpha(db>=-30+group*3?1.f:.12f)); g.fillRect(r.x+group*33.5f+led*7.8f,r.y+row*8,5.5f,5.5f); }
        }
        if(processor.engine.meters.protectionGain.load()<.98f) {g.setColour(juce::Colour(0xffffb041));g.setFont(juce::Font(juce::FontOptions(11).withStyle("Bold")));g.drawText("LIMIT",552,238,80,17,juce::Justification::centredRight);}
        g.setColour(juce::Colour(0xff040303)); g.fillRect(924.f,146.f,121.f,66.f);
        const int bpm=std::clamp(static_cast<int>(std::round(processor.engine.meters.tempo.load())),0,999);
        constexpr std::array<int,10> segments{0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
        for(int d=0;d<3;++d) { const int n=d==0?bpm/100:d==1?(bpm/10)%10:bpm%10; const float x=934.f+d*36,y=156; const float lines[7][4]={{x+5,y,x+25,y},{x+27,y+3,x+25,y+22},{x+24,y+27,x+22,y+46},{x+1,y+49,x+20,y+49},{x-1,y+27,x-3,y+46},{x+2,y+3,x,y+22},{x+2,y+24,x+23,y+24}};
            for(int i=0;i<7;++i) { g.setColour(segments[static_cast<size_t>(n)]&(1<<i)?juce::Colour(0xfff28d1e):juce::Colour(0xff1c0c03)); g.drawLine(lines[i][0],lines[i][1],lines[i][2],lines[i][3],5); }
        }
        for(int i=0;i<4;++i) if(value(Param::SampleSource)<.5f||i!=static_cast<int>(value(Param::Bank))) { g.setColour(juce::Colours::black.withAlpha(.6f)); g.fillRoundedRectangle(488.f+i*115,590,30,23,3); }
        const auto stripValues=processor.engine.params.snapshot();
        for(unsigned position=0;position<8;++position) {
            const float x=475.f+position*51;
            g.setColour(juce::Colour(0xff2ed1de));g.setFont(juce::Font(juce::FontOptions(14).withStyle("Bold")));
            g.drawText(juce::String(rmx::xPadBeatNames[rmx::xPadBeatChoice(stripValues,static_cast<float>(position))].data()),static_cast<int>(x),775,47,20,juce::Justification::centred);
        }
        hardwareSwitch(g,{1884,430,113,105},{1891,435+value(Param::ReleaseAmount)*62,99,30});
        hardwareSwitch(g,{1903,301,61,47},{1908+(2-value(Param::ReleaseType))*17,307,15,34});
        hardwareSwitch(g,{1831,151,69,43},{1836+value(Param::UserSettings)*29,156,29,33});
    }
    void mouseDown(const juce::MouseEvent& event) override {
        grabKeyboardFocus(); auto pos=point(event);
        if(event.mods.isPopupMenu()) { menu(); return; }
        const int scene=rmx::panel::sceneAt(pos.x,pos.y);
        if(scene>=0) { const bool same=static_cast<int>(value(Param::SceneType))==scene&&value(Param::SceneOn)>.5f; processor.change(Param::SceneType,static_cast<float>(scene)); processor.change(Param::SceneOn,same?0:1); return; }
        for(size_t i=0;i<controls.size();++i) {
            const auto& c=controls[i]; if(!rect(c.rect).contains(pos)) continue;
            if(c.kind==Kind::Pad) selectedPad=static_cast<int>(c.value);
            if(c.action==7) { dragging=static_cast<int>(i); processor.engine.enqueue({rmx::EventType::NudgeStart,0,c.value}); return; }
            if(rmx::panel::activate(c,[&](Param p){ return value(p); },[&](Param p,float v){ processor.change(p,v); },[&](rmx::Event e){ processor.engine.enqueue(e); },event.mods.isShiftDown(),event.mods.isAltDown())) return;
            if(c.kind==Kind::Action) { if(c.action==1) menu(); }
            else {
                dragging=static_cast<int>(i); dragOrigin=pos; dragValue=value(c.param); parameter(c.param)->beginChangeGesture();
                if(c.kind==Kind::Strip) { setGesture(c.param,std::clamp((pos.x-c.rect.x)/c.rect.w*8,0.f,7.f)); processor.engine.enqueue({rmx::EventType::RollStart,static_cast<uint8_t>(selectedPad)}); }
                if(c.kind==Kind::Lever) setGesture(c.param,std::clamp((pos.y-c.rect.y)/c.rect.h,0.f,1.f));
            }
            break;
        }
    }
    void mouseDrag(const juce::MouseEvent& event) override {
        if(dragging<0) return; const auto& c=controls[static_cast<size_t>(dragging)]; auto pos=point(event); const auto& info=rmx::parameters[static_cast<size_t>(c.param)];
        if(c.kind==Kind::Knob) { setGesture(c.param,dragValue+(dragOrigin.y-pos.y)*(info.max-info.min)/250*(event.mods.isShiftDown()?.12f:1.f)); if(c.param==Param::SceneDepth) processor.change(Param::SceneOn,1); }
        if(c.kind==Kind::Lever) setGesture(c.param,std::clamp((pos.y-c.rect.y)/c.rect.h,0.f,1.f));
        if(c.kind==Kind::Strip) setGesture(c.param,std::clamp((pos.x-c.rect.x)/c.rect.w*8,0.f,7.f));
    }
    void mouseUp(const juce::MouseEvent&) override { finishGesture(); }
    void mouseDoubleClick(const juce::MouseEvent& event) override { const auto pos=point(event); for(const auto& c:controls) if(c.kind==Kind::Knob&&rect(c.rect).contains(pos)) { processor.change(c.param,rmx::parameters[static_cast<size_t>(c.param)].initial); break; } }
    bool keyPressed(const juce::KeyPress& key) override {
        const auto c=key.getTextCharacter(); if(c>='1'&&c<='4') { selectedPad=c-'1'; processor.engine.enqueue({rmx::EventType::Trigger,static_cast<uint8_t>(selectedPad)}); return true; }
        if(key==juce::KeyPress::spaceKey) { toggle(Param::Bypass); return true; }
        if(key==juce::KeyPress::escapeKey) { processor.engine.enqueue({rmx::EventType::Panic}); return true; }
        if(c=='t'||c=='T') { processor.engine.enqueue({rmx::EventType::Tap}); return true; } return false;
    }
private:
    static void hardwareSwitch(juce::Graphics& g,juce::Rectangle<float> r,juce::Rectangle<float> cap) {
        g.setGradientFill(juce::ColourGradient(juce::Colour(0xff0a0d0b),0,r.getY(),juce::Colour(0xff6b756e),0,r.getBottom(),false));g.fillRoundedRectangle(r.expanded(2),4);
        g.setColour(juce::Colour(0xff060908));g.fillRoundedRectangle(r,3);
        g.setGradientFill(juce::ColourGradient(juce::Colour(0xffa8b5ab),0,cap.getY(),juce::Colour(0xff38453b),0,cap.getBottom(),false));g.fillRoundedRectangle(cap,3);
        g.setColour(juce::Colour(0xb31f2b21));for(int i=0;i<3;++i)g.fillRect(cap.getX()+5,cap.getY()+8+i*5,cap.getWidth()-10,1.f);
    }
    static juce::Rectangle<float> rect(rmx::panel::Rect r) { return {r.x,r.y,r.w,r.h}; }
    juce::Point<float> point(const juce::MouseEvent& e) const { return {e.position.x*2048/getWidth(),e.position.y*921/getHeight()}; }
    float value(Param p) const { return processor.tree.getRawParameterValue(js(rmx::parameters[static_cast<size_t>(p)].id))->load(); }
    juce::RangedAudioParameter* parameter(Param p) { return processor.tree.getParameter(js(rmx::parameters[static_cast<size_t>(p)].id)); }
    void toggle(Param p) { processor.change(p,value(p)>.5?0:1); }
    void setGesture(Param p,float v) { auto* param=parameter(p); param->setValueNotifyingHost(param->convertTo0to1(rmx::sanitize(p,v))); }
    void finishGesture() { if(dragging<0) return; auto c=controls[static_cast<size_t>(dragging)]; if(c.action==7) { processor.engine.enqueue({rmx::EventType::NudgeStop}); dragging=-1; return; } if(c.kind==Kind::Lever) setGesture(c.param,0); if(c.kind==Kind::Strip) processor.engine.enqueue({rmx::EventType::RollStop}); parameter(c.param)->endChangeGesture(); dragging=-1; }
    void timerCallback() override { repaint(); }
    void menu() {
        juce::PopupMenu menu; menu.addItem(1,"All parameters / exact values…"); menu.addItem(2,"Import sample into selected pad…");menu.addItem(7,"Selected sample playback…"); menu.addItem(3,"Save preset…"); menu.addItem(4,"Load preset…"); menu.addSeparator(); menu.addItem(5,"Bypass",true,value(Param::Bypass)>.5f); menu.addItem(6,"Reset effects");
        menu.showMenuAsync(juce::PopupMenu::Options{}.withTargetComponent(this),[safe=juce::Component::SafePointer<RMXEditor>(this)](int result) { if(!safe) return; switch(result) { case 1: safe->settings(); break; case 2: safe->files(0); break; case 3: safe->files(1); break; case 4: safe->files(2); break; case 5: safe->toggle(Param::Bypass); break; case 6: safe->processor.engine.enqueue({rmx::EventType::Panic}); break;case 7:safe->sampleSettings();break; } });
    }
    void sampleSettings() {
        const int slot=static_cast<int>(value(Param::Bank))*4+selectedPad;
        const auto playback=processor.samplePlayback(slot);
        auto dialog=std::make_shared<juce::AlertWindow>("Sample playback","Only slot 1 of each bank can loop. Set the sample's original BPM; loops follow the performance tempo.",juce::MessageBoxIconType::NoIcon,this);
        dialog->addComboBox("mode",juce::StringArray{"One-shot","Loop"},"Playback");
        dialog->getComboBoxComponent("mode")->setSelectedItemIndex(playback.loop?1:0);
        dialog->getComboBoxComponent("mode")->setEnabled(slot%4==0);
        dialog->addTextEditor("bpm",juce::String(playback.bpm,3),"Sample BPM (70–200)");
        dialog->addButton("Apply",1,juce::KeyPress(juce::KeyPress::returnKey));dialog->addButton("Cancel",0,juce::KeyPress(juce::KeyPress::escapeKey));
        dialog->enterModalState(true,juce::ModalCallbackFunction::create([safe=juce::Component::SafePointer<RMXEditor>(this),dialog,slot](int result) {
            if(!safe||result!=1)return;
            try {
                const auto text=dialog->getTextEditorContents("bpm").trim().toStdString();size_t consumed=0;const double bpm=std::stod(text,&consumed);
                if(consumed!=text.size())throw std::runtime_error("Enter a sample BPM between 70 and 200");
                safe->processor.configureSample(slot,{bpm,dialog->getComboBoxComponent("mode")->getSelectedItemIndex()==1});
            } catch(const std::exception& error) {safe->processor.assetMessage=error.what();}
        }),false);
    }
    void settings() { juce::DialogWindow::LaunchOptions options; options.dialogTitle="RMX · Engine parameters"; options.dialogBackgroundColour=juce::Colour(0xff131a24); options.useNativeTitleBar=true; options.resizable=true; auto* editor=new juce::GenericAudioProcessorEditor(processor); editor->setSize(620,700); options.content.setOwned(editor); options.launchAsync(); }
    void files(int mode) {
        chooser=std::make_unique<juce::FileChooser>(mode==0?"Import sample":mode==1?"Save preset":"Load preset",juce::File{},mode==0?"*.wav":"*.rmx"); const int slot=static_cast<int>(value(Param::Bank))*4+selectedPad;
        const int flags=(mode==1?juce::FileBrowserComponent::saveMode|juce::FileBrowserComponent::warnAboutOverwriting:juce::FileBrowserComponent::openMode)|juce::FileBrowserComponent::canSelectFiles;
        chooser->launchAsync(flags,[safe=juce::Component::SafePointer<RMXEditor>(this),mode,slot](const juce::FileChooser& choice) { if(!safe||choice.getResult()==juce::File{}) return; try { if(mode==0) safe->processor.importSample(slot,choice.getResult()); else if(mode==1) safe->processor.save(choice.getResult()); else safe->processor.load(choice.getResult()); } catch(const std::exception& e) { safe->processor.assetMessage=e.what(); } });
    }
};
