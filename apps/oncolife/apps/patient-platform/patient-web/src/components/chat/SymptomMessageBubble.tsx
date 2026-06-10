import React, { useState } from 'react';
import type { Message } from '../../types/chat';
import { formatTimeForDisplay } from '@oncolife/shared-utils';

interface SymptomGroup {
  name: string;
  icon: string;
  symptoms: { id: string; name: string; available?: boolean }[];
}

interface SymptomMessageBubbleProps {
  message: Message;
  onOptionSelect?: (value: string | boolean) => void;
  onMultiSelectSubmit?: (values: string[]) => void;
  onSymptomSelect?: (symptomIds: string[]) => void;
  onDisclaimerAccept?: () => void;
  onEmergencyCheck?: (selected: string[]) => void;
  onSummaryAction?: (action: string) => void;
  shouldShowInteractive?: boolean;
}

// Check icon SVG component
const CheckIcon: React.FC = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

// Ruby avatar component
const RubyAvatar: React.FC<{ mini?: boolean; emoji?: string }> = ({ mini, emoji }) => (
  <div className={mini ? 'mini-avatar' : 'ruby-avatar'}>
    {emoji || '💎'}
  </div>
);

// System avatar for disclaimer/emergency screens
const SystemAvatar: React.FC = () => (
  <div className="system-avatar">⚕️</div>
);

// Format user response for better display
const formatUserResponse = (content: string): string => {
  const friendlyLabels: Record<string, string> = {
    'accept': 'I Understand',
    'none': 'None of these',
    'acknowledge': 'I Understand',
    'call_911': 'Calling 911',
    'save_diary': 'Save to Diary',
    'download': 'Download Summary',
    'report_another': 'Report Another',
    'done': 'Done',
    'go_diary': 'Go to Diary',
    'continue': 'Continue',
    'yes': 'Yes',
    'no': 'No',
    'true': 'Yes',
    'false': 'No',
    // Patient context (chemo dates, physician visit)
    'today': 'Today',
    '1d': '1 day ago',
    '2-3d': '2-3 days ago',
    '4-7d': '4-7 days ago',
    '1-2w': '1-2 weeks ago',
    '>2w': 'More than 2 weeks ago',
    'this_week': 'This week',
    'next_week': 'Next week',
    'not_scheduled': 'Not scheduled yet',
  };
  
  // Remove any line breaks that might be in the content
  const cleanContent = content.replace(/\n/g, ' ').trim();
  
  // Check for exact match (case insensitive)
  const lowerContent = cleanContent.toLowerCase();
  if (friendlyLabels[lowerContent]) {
    return friendlyLabels[lowerContent];
  }
  
  // Check for comma-separated selections
  if (cleanContent.includes(',')) {
    const items = cleanContent.split(',').map(s => s.trim()).filter(s => s);
    if (items.length > 0) {
      return items.join(', ');
    }
  }
  
  // Return cleaned content
  return cleanContent;
};

export const SymptomMessageBubble: React.FC<SymptomMessageBubbleProps> = ({
  message,
  onOptionSelect,
  onMultiSelectSubmit,
  onSymptomSelect,
  onDisclaimerAccept,
  onEmergencyCheck,
  onSummaryAction,
  shouldShowInteractive = false,
}) => {
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [selectedEmergencies, setSelectedEmergencies] = useState<string[]>([]);
  
  const isUser = message.sender === 'user';
  const frontendType = message.structured_data?.frontend_type || message.message_type;
  const options = message.structured_data?.options_data || 
                  message.structured_data?.options?.map((opt: string) => ({ label: opt, value: opt })) || 
                  [];
  const symptomGroups = message.structured_data?.symptom_groups as Record<string, SymptomGroup> | undefined;
  const sender = message.structured_data?.sender || 'ruby';
  const avatar = message.structured_data?.avatar;

  // Handle single option selection (yes/no, choice)
  const handleOptionClick = (value: string | boolean) => {
    if (onOptionSelect) {
      onOptionSelect(value);
    }
  };

  // Handle multi-select toggle
  const handleMultiToggle = (value: string) => {
    setSelectedOptions(prev => {
      if (prev.includes(value)) {
        return prev.filter(v => v !== value);
      } else {
        return [...prev, value];
      }
    });
  };

  // Handle multi-select submit
  const handleMultiSubmit = () => {
    if (onMultiSelectSubmit && selectedOptions.length > 0) {
      onMultiSelectSubmit(selectedOptions);
      setSelectedOptions([]);
    }
  };

  // Handle symptom selection toggle
  const handleSymptomToggle = (symptomId: string) => {
    setSelectedSymptoms(prev => {
      if (prev.includes(symptomId)) {
        return prev.filter(s => s !== symptomId);
      } else {
        return [...prev, symptomId];
      }
    });
  };

  // Handle symptom selection submit
  const handleSymptomSubmit = () => {
    if (onSymptomSelect) {
      onSymptomSelect(selectedSymptoms.length > 0 ? selectedSymptoms : ['none']);
      setSelectedSymptoms([]);
    }
  };

  // Handle emergency symptom toggle
  const handleEmergencyToggle = (symptomId: string) => {
    setSelectedEmergencies(prev => {
      if (prev.includes(symptomId)) {
        return prev.filter(s => s !== symptomId);
      } else {
        return [...prev, symptomId];
      }
    });
  };

  // Handle emergency check submit
  const handleEmergencySubmit = (isNone: boolean) => {
    if (onEmergencyCheck) {
      if (isNone) {
        onEmergencyCheck(['none']);
      } else {
        onEmergencyCheck(selectedEmergencies);
      }
      setSelectedEmergencies([]);
    }
  };

  // Format message content with markdown-style bold and line breaks
  const formatContent = (content: string) => {
    // Replace **text** with <strong>text</strong>
    let formatted = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Replace newlines with <br>
    formatted = formatted.replace(/\n/g, '<br>');
    // Replace --- with horizontal rule
    formatted = formatted.replace(/<br>---<br>/g, '<hr class="chat-divider">');
    return { __html: formatted };
  };

  // =========================================================================
  // RENDER: Medical Disclaimer Screen
  // =========================================================================
  const renderDisclaimer = () => {
    return (
      <div className="disclaimer-screen">
        <div className="disclaimer-icon">⚠️</div>
        <div className="disclaimer-content">
          <h2>Medical Disclaimer</h2>
          <div className="disclaimer-text" dangerouslySetInnerHTML={formatContent(message.content)} />
        </div>
        <button 
          className="disclaimer-accept-btn"
          onClick={() => onDisclaimerAccept && onDisclaimerAccept()}
        >
          ✓ I Understand - Start Triage
        </button>
      </div>
    );
  };

  // =========================================================================
  // RENDER: Emergency Check Screen
  // =========================================================================
  const renderEmergencyCheck = () => {
    // Filter for emergency options, or show all if is_emergency field doesn't exist
    const emergencyOptions = options.filter((o: any) => o.is_emergency !== false && o.style !== 'secondary');
    
    return (
      <div className="emergency-check-screen">
        <div className="emergency-header">
          <div className="emergency-icon">🚨</div>
          <h2>Urgent Safety Check</h2>
        </div>
        <p className="emergency-subtitle">
          Before we assess your symptoms, we need to rule out immediate emergencies.
        </p>
        <p className="emergency-instruction">
          <strong>Please select any of the following you are currently experiencing:</strong>
        </p>
        
        <div className="emergency-options">
          {emergencyOptions.map((opt: any) => (
            <button
              key={opt.value}
              className={`emergency-option ${selectedEmergencies.includes(opt.value) ? 'selected' : ''}`}
              onClick={() => handleEmergencyToggle(opt.value)}
            >
              <span className="emergency-checkbox">
                {selectedEmergencies.includes(opt.value) && <CheckIcon />}
              </span>
              <span className="emergency-label">{opt.label}</span>
            </button>
          ))}
        </div>

        <div className="emergency-actions">
          {selectedEmergencies.length > 0 ? (
            <button 
              className="emergency-continue-btn emergency"
              onClick={() => handleEmergencySubmit(false)}
            >
              Continue with {selectedEmergencies.length} Selected
            </button>
          ) : (
            <button 
              className="emergency-continue-btn safe"
              onClick={() => handleEmergencySubmit(true)}
            >
              ✓ None of these - Continue
            </button>
          )}
        </div>
      </div>
    );
  };

  // =========================================================================
  // RENDER: Grouped Symptom Selector
  // =========================================================================
  const renderGroupedSymptomSelector = () => {
    if (!symptomGroups) {
      return renderLegacySymptomSelector();
    }

    return (
      <div className="grouped-symptom-selector">
        <div className="symptom-instruction">
          <p>What symptoms are you experiencing today?</p>
          <span className="instruction-hint">Select all that apply, then tap Continue</span>
        </div>

        {Object.entries(symptomGroups).map(([groupId, group]) => (
          <div key={groupId} className="symptom-group">
            <div className="group-header">
              <span className="group-icon">{group.icon}</span>
              <span className="group-name">{group.name}</span>
            </div>
            <div className="symptom-grid">
              {group.symptoms.map((symptom) => (
                <button
                  key={symptom.id}
                  className={`symptom-chip ${selectedSymptoms.includes(symptom.id) ? 'selected' : ''}`}
                  onClick={() => handleSymptomToggle(symptom.id)}
                  disabled={!symptom.available}
                >
                  <span className="chip-checkbox">
                    {selectedSymptoms.includes(symptom.id) && <CheckIcon />}
                  </span>
                  <span className="chip-label">{symptom.name}</span>
                </button>
              ))}
            </div>
          </div>
        ))}

        <div className="symptom-actions">
          <button 
            className="symptom-continue-btn primary"
            onClick={handleSymptomSubmit}
            disabled={selectedSymptoms.length === 0}
          >
            Continue ({selectedSymptoms.length} selected)
          </button>
          <button 
            className="symptom-continue-btn secondary"
            onClick={() => onSymptomSelect && onSymptomSelect(['none'])}
          >
            ✨ I'm feeling fine today
          </button>
        </div>
      </div>
    );
  };

  // Legacy symptom selector (flat list)
  const renderLegacySymptomSelector = () => {
    const optionsData = message.structured_data?.options_data || [];
    
    // Group by category
    const emergency = optionsData.filter((o: any) => o.category === 'emergency');
    const common = optionsData.filter((o: any) => o.category === 'common');
    const other = optionsData.filter((o: any) => o.category === 'other');
    const none = optionsData.filter((o: any) => o.category === 'none');

    return (
      <div className="symptom-selector">
        {emergency.length > 0 && (
          <div className="symptom-category">
            <div className="category-label emergency">🚨 Emergency Symptoms</div>
            <div className="symptom-grid">
              {emergency.map((opt: any) => (
                <button
                  key={opt.value}
                  className={`symptom-chip emergency ${selectedSymptoms.includes(opt.value) ? 'selected' : ''}`}
                  onClick={() => handleSymptomToggle(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {common.length > 0 && (
          <div className="symptom-category">
            <div className="category-label">Common Side Effects</div>
            <div className="symptom-grid">
              {common.map((opt: any) => (
                <button
                  key={opt.value}
                  className={`symptom-chip ${selectedSymptoms.includes(opt.value) ? 'selected' : ''}`}
                  onClick={() => handleSymptomToggle(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {other.length > 0 && (
          <div className="symptom-category">
            <div className="category-label">Other Symptoms</div>
            <div className="symptom-grid">
              {other.map((opt: any) => (
                <button
                  key={opt.value}
                  className={`symptom-chip ${selectedSymptoms.includes(opt.value) ? 'selected' : ''}`}
                  onClick={() => handleSymptomToggle(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {none.length > 0 && (
          <div className="symptom-category">
            <div className="symptom-grid">
              {none.map((opt: any) => (
                <button
                  key={opt.value}
                  className={`symptom-chip ${selectedSymptoms.includes(opt.value) ? 'selected' : ''}`}
                  onClick={() => handleSymptomToggle(opt.value)}
                >
                  ✨ {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <button 
          className="multi-select-submit"
          onClick={handleSymptomSubmit}
          disabled={selectedSymptoms.length === 0}
        >
          Continue ({selectedSymptoms.length} selected)
        </button>
      </div>
    );
  };

  // =========================================================================
  // RENDER: Summary Screen
  // =========================================================================
  const renderSummary = () => {
    const summaryData = message.structured_data?.summary_data;
    const triageLevel = message.structured_data?.triage_level;
    
    let summaryClass = 'ok';
    if (triageLevel === 'call_911') {
      summaryClass = 'emergency';
    } else if (triageLevel === 'notify_care_team' || triageLevel === 'urgent') {
      summaryClass = 'alert';
    }

    return (
      <div className={`summary-screen ${summaryClass}`}>
        <div className="summary-content" dangerouslySetInnerHTML={formatContent(message.content)} />
        
        <div className="summary-actions">
          {options.map((opt: any) => (
            <button
              key={opt.value}
              className={`summary-action-btn ${opt.style || 'default'}`}
              onClick={() => onSummaryAction && onSummaryAction(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    );
  };

  // =========================================================================
  // RENDER: Emergency Result
  // =========================================================================
  const renderEmergencyResult = () => {
    return (
      <div className="emergency-result">
        <div className="emergency-result-header">
          <span className="emergency-pulse">🚨</span>
          <h2>EMERGENCY</h2>
        </div>
        <div className="emergency-result-content" dangerouslySetInnerHTML={formatContent(message.content)} />
        <div className="emergency-result-actions">
          <a href="tel:911" className="call-911-btn">
            📞 Call 911
          </a>
          <button 
            className="acknowledge-btn"
            onClick={() => onSummaryAction && onSummaryAction('acknowledge')}
          >
            I Understand
          </button>
        </div>
      </div>
    );
  };

  // Render triage result with special styling
  const renderTriageResult = () => {
    const triageLevel = message.structured_data?.triage_level;
    let triageClass = 'ok';
    
    if (triageLevel === 'call_911') {
      triageClass = 'emergency';
    } else if (triageLevel === 'notify_care_team' || triageLevel === 'urgent') {
      triageClass = 'alert';
    }

    return (
      <div className={`triage-result ${triageClass}`}>
        <div 
          className="message-content" 
          dangerouslySetInnerHTML={formatContent(message.content)}
        />
      </div>
    );
  };

  // Render interactive options based on type
  const renderInteractive = () => {
    if (!shouldShowInteractive || !options.length) return null;

    // Symptom selector (grouped)
    if (frontendType === 'symptom-select' || frontendType === 'symptom_select') {
      return renderGroupedSymptomSelector();
    }

    // Yes/No or single choice
    if (frontendType === 'yes_no' || frontendType === 'single-select' || frontendType === 'choice') {
      return (
        <div className="message-options">
          {options.map((opt: any, index: number) => (
            <button
              key={index}
              className={`option-btn ${opt.style || ''}`}
              onClick={() => handleOptionClick(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      );
    }

    // Multi-select
    if (frontendType === 'multi-select' || frontendType === 'multiselect') {
      return (
        <div className="multi-select-container">
          {options.map((opt: any, index: number) => (
            <div
              key={index}
              className={`multi-option ${selectedOptions.includes(opt.value) ? 'selected' : ''}`}
              onClick={() => handleMultiToggle(opt.value)}
            >
              <div className="checkbox-custom">
                <CheckIcon />
              </div>
              <span className="multi-option-label">{opt.label}</span>
            </div>
          ))}
          <button 
            className="multi-select-submit"
            onClick={handleMultiSubmit}
            disabled={selectedOptions.length === 0}
          >
            Submit Selection
          </button>
        </div>
      );
    }

    // Default: render options as action buttons (for text messages with options)
    // This handles cases like "notes saved" with follow-up action buttons
    if (options.length > 0) {
      return (
        <div className="message-options action-options">
          {options.map((opt: any, index: number) => (
            <button
              key={index}
              className={`option-btn action-btn ${opt.style || 'default'}`}
              onClick={() => onSummaryAction ? onSummaryAction(opt.value) : handleOptionClick(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      );
    }

    return null;
  };

  // =========================================================================
  // MAIN RENDER
  // =========================================================================

  // Handle special screen types (full-screen UI)
  if (frontendType === 'disclaimer' && shouldShowInteractive) {
    return renderDisclaimer();
  }

  if ((frontendType === 'emergency-check' || frontendType === 'emergency_check') && shouldShowInteractive) {
    return renderEmergencyCheck();
  }

  if (frontendType === 'emergency' && shouldShowInteractive) {
    return renderEmergencyResult();
  }

  if (frontendType === 'summary' && shouldShowInteractive) {
    return renderSummary();
  }

  // Patient context (last chemo, physician visit) - card with options
  if (frontendType === 'patient_context' && shouldShowInteractive) {
    return (
      <div className="patient-context-screen">
        <div className="context-card">
          <RubyAvatar emoji="💎" />
          <div 
            className="context-message"
            dangerouslySetInnerHTML={formatContent(message.content)}
          />
          <div className="context-options">
            {options.map((opt: any, index: number) => (
              <button
                key={index}
                className="context-option-btn"
                onClick={() => handleOptionClick(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Check if this is a triage result
  const isTriageResult = message.structured_data?.is_complete === true;

  // WhatsApp-style chat bubble
  return (
    <div className={`message-wrapper ${isUser ? 'user' : 'assistant'} ${sender === 'system' ? 'system' : ''}`}>
      {!isUser && (
        <div className="message-with-avatar">
          {sender === 'system' ? (
            <SystemAvatar />
          ) : (
            <RubyAvatar mini emoji={avatar} />
          )}
          <div className="message-container">
            <div className="message-bubble">
              {isTriageResult ? (
                renderTriageResult()
              ) : (
                <div 
                  className="message-content"
                  dangerouslySetInnerHTML={formatContent(message.content)}
                />
              )}
              {renderInteractive()}
            </div>
            <div className="message-time">
              {formatTimeForDisplay(message.created_at)}
            </div>
          </div>
        </div>
      )}
      {isUser && (
        <div className="user-message-container">
          <div className="message-bubble user-bubble">
            <div className="message-content">{formatUserResponse(message.content)}</div>
          </div>
          <div className="message-time">
            {formatTimeForDisplay(message.created_at)}
          </div>
        </div>
      )}
    </div>
  );
};
