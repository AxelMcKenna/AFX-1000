#include "HardwareEditor.h"
#include "RMXProcessor.h"
juce::AudioProcessorEditor* RMXProcessor::createEditor() {
    return new RMXEditor(*this);
}
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() {
    return new RMXProcessor;
}
