import React, { useState } from 'react';
import { X, Calendar } from 'lucide-react';

interface CalendarModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDateSelect: (date: Date) => void;
}

export const CalendarModal: React.FC<CalendarModalProps> = ({
  isOpen,
  onClose,
  onDateSelect
}) => {
  const [selectedDate, setSelectedDate] = useState<string>('');

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (selectedDate) {
      const date = new Date(selectedDate);
      onDateSelect(date);
      onClose();
    }
  };


  const getMaxDate = () => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  };

  return (
    <div className="calendar-modal-overlay">
      <div className="calendar-modal">
        <div className="calendar-modal-header">
          <h3>
            <Calendar size={20} style={{ marginRight: '8px' }} />
            Select Chemotherapy Date
          </h3>
          <button onClick={onClose} className="close-button">
            <X size={20} />
          </button>
        </div>
        
        <div className="calendar-modal-content">
          <p>When did you receive chemotherapy?</p>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            max={getMaxDate()}
            className="date-input"
          />
        </div>
        
        <div className="calendar-modal-footer">
          <button onClick={onClose} className="cancel-button">
            Cancel
          </button>
          <button 
            onClick={handleSubmit} 
            disabled={!selectedDate}
            className="confirm-button"
          >
            Confirm Date
          </button>
        </div>
      </div>
    </div>
  );
}; 