/**
 * OncoLife Dark Mode Toggle Component
 * Animated toggle switch for light/dark mode
 */

import React from 'react';
import styled from 'styled-components';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { Moon, Sun } from 'lucide-react';
import { useThemeMode } from '../../contexts/ThemeContext';

// =============================================================================
// STYLED COMPONENTS
// =============================================================================

const ToggleButton = styled(IconButton)<{ $isDark: boolean }>`
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: ${props => props.$isDark 
    ? 'linear-gradient(135deg, #1E3A5F 0%, #2E5077 100%)' 
    : 'linear-gradient(135deg, #F5F7FA 0%, #E2E8F0 100%)'
  };
  transition: all 0.3s ease;
  overflow: hidden;
  
  &:hover {
    transform: scale(1.05);
    box-shadow: ${props => props.$isDark
      ? '0 4px 12px rgba(59, 130, 246, 0.3)'
      : '0 4px 12px rgba(0, 0, 0, 0.1)'
    };
  }
  
  .icon {
    position: absolute;
    transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }
  
  .sun-icon {
    color: #F59E0B;
    opacity: ${props => props.$isDark ? 0 : 1};
    transform: ${props => props.$isDark ? 'rotate(-90deg) scale(0)' : 'rotate(0) scale(1)'};
  }
  
  .moon-icon {
    color: #60A5FA;
    opacity: ${props => props.$isDark ? 1 : 0};
    transform: ${props => props.$isDark ? 'rotate(0) scale(1)' : 'rotate(90deg) scale(0)'};
  }
`;

const PillToggle = styled.button<{ $isDark: boolean }>`
  position: relative;
  display: flex;
  align-items: center;
  width: 72px;
  height: 36px;
  padding: 4px;
  border-radius: 18px;
  border: 2px solid ${props => props.$isDark ? '#334155' : '#E2E8F0'};
  background: ${props => props.$isDark 
    ? 'linear-gradient(135deg, #1E293B 0%, #334155 100%)' 
    : 'linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%)'
  };
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: ${props => props.$isDark
      ? '0 0 0 3px rgba(59, 130, 246, 0.2)'
      : '0 0 0 3px rgba(0, 137, 123, 0.15)'
    };
  }
  
  &:focus-visible {
    outline: none;
    box-shadow: ${props => props.$isDark
      ? '0 0 0 3px rgba(59, 130, 246, 0.4)'
      : '0 0 0 3px rgba(0, 137, 123, 0.3)'
    };
  }
`;

const ToggleKnob = styled.div<{ $isDark: boolean }>`
  position: absolute;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: ${props => props.$isDark 
    ? 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)' 
    : 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)'
  };
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  transform: translateX(${props => props.$isDark ? '34px' : '0'});
  
  svg {
    color: white;
    width: 16px;
    height: 16px;
  }
`;

const IconsContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 6px;
  
  svg {
    width: 14px;
    height: 14px;
    transition: all 0.3s ease;
  }
`;

// =============================================================================
// COMPONENT
// =============================================================================

interface DarkModeToggleProps {
  variant?: 'icon' | 'pill';
  size?: 'small' | 'medium';
  showTooltip?: boolean;
}

export const DarkModeToggle: React.FC<DarkModeToggleProps> = ({
  variant = 'icon',
  size = 'medium',
  showTooltip = true,
}) => {
  const { isDark, toggleTheme, mode } = useThemeMode();

  const tooltipText = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';

  if (variant === 'pill') {
    const toggle = (
      <PillToggle
        $isDark={isDark}
        onClick={toggleTheme}
        role="switch"
        aria-checked={isDark}
        aria-label={tooltipText}
      >
        <IconsContainer>
          <Sun 
            size={14} 
            style={{ 
              color: isDark ? '#64748B' : '#F59E0B',
              opacity: isDark ? 0.5 : 1,
            }} 
          />
          <Moon 
            size={14} 
            style={{ 
              color: isDark ? '#60A5FA' : '#94A3B8',
              opacity: isDark ? 1 : 0.5,
            }} 
          />
        </IconsContainer>
        <ToggleKnob $isDark={isDark}>
          {isDark ? <Moon size={16} /> : <Sun size={16} />}
        </ToggleKnob>
      </PillToggle>
    );

    if (showTooltip) {
      return <Tooltip title={tooltipText} arrow>{toggle}</Tooltip>;
    }
    return toggle;
  }

  // Icon variant
  const iconToggle = (
    <ToggleButton
      $isDark={isDark}
      onClick={toggleTheme}
      aria-label={tooltipText}
      size={size}
    >
      <Sun className="icon sun-icon" size={size === 'small' ? 18 : 22} />
      <Moon className="icon moon-icon" size={size === 'small' ? 18 : 22} />
    </ToggleButton>
  );

  if (showTooltip) {
    return <Tooltip title={tooltipText} arrow>{iconToggle}</Tooltip>;
  }
  return iconToggle;
};

export default DarkModeToggle;



