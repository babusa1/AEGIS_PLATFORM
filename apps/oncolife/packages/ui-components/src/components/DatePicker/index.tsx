import React, { useState } from 'react';
import { DatePicker as MUIDatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { Dayjs } from 'dayjs';
import { Calendar } from 'lucide-react';
import { DatePickerContainer, DateDisplayButton } from './DatePicker.styles';

interface SharedDatePickerProps {
  value: Dayjs;
  onChange: (date: Dayjs) => void;
  label?: string;
  views?: ('month' | 'year')[];
  fullWidth?: boolean;
}

const SharedDatePicker: React.FC<SharedDatePickerProps> = ({
  value,
  onChange,
  label = 'Select Month & Year',
  views = ['month', 'year'],
  fullWidth = false,
}) => {
  const [open, setOpen] = useState(false);

  const handleDateChange = (newDate: Dayjs | null) => {
    if (newDate) {
      onChange(newDate);
      setOpen(false);
    }
  };

  const formatCurrentDate = (date: Dayjs) => date.format('MMMM YYYY');

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <DatePickerContainer $fullWidth={fullWidth}>
        {open ? (
          <MUIDatePicker
            label={label}
            views={views}
            value={value}
            onChange={handleDateChange}
            open={true}
            onClose={() => setOpen(false)}
            slotProps={{
              textField: {
                size: 'small',
                sx: {
                  '& .MuiInputBase-root': { 
                    height: '40px',
                    width: fullWidth ? '100%' : 'auto'
                  },
                  '& .MuiInputLabel-root': { fontSize: '14px' },
                  width: fullWidth ? '100%' : 'auto'
                },
              },
            }}
          />
        ) : (
          <DateDisplayButton onClick={() => setOpen(true)} $fullWidth={fullWidth}>
            <span>{formatCurrentDate(value)}</span>
            <Calendar />
          </DateDisplayButton>
        )}
      </DatePickerContainer>
    </LocalizationProvider>
  );
};

export default SharedDatePicker; 