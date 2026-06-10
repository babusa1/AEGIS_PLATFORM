/**
 * OncoLife Physician Portal - Layout
 * 
 * Responsive layout with:
 * - Desktop: Sidebar navigation (dark theme)
 * - Mobile: Hamburger drawer
 * - Dark mode toggle
 * - Page transition animations
 */

import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useTheme, useMediaQuery } from '@mui/material';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Avatar from '@mui/material/Avatar';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import { 
  LayoutDashboard,
  Users,
  UserCog,
  Menu as MenuIcon,
  LogOut,
  X,
  Activity,
  Moon,
  Sun,
  FileText
} from 'lucide-react';
import { useUser } from '../contexts/UserContext';
import { DarkModeToggle, useThemeMode } from '@oncolife/ui-components';

// Sidebar width
const DRAWER_WIDTH = 260;

// Navigation items
const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { id: 'patients', label: 'Patients', icon: Users, path: '/patients' },
  { id: 'reports', label: 'Weekly Reports', icon: FileText, path: '/reports' },
  { id: 'staff', label: 'Staff', icon: UserCog, path: '/staff' },
];

const Layout: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { profile } = useUser();
  const { isDark } = useThemeMode();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Sidebar colors based on dark mode
  const sidebarBg = isDark ? theme.palette.background.paper : theme.palette.primary.main;
  const sidebarText = isDark ? theme.palette.text.primary : 'white';
  const sidebarTextMuted = isDark ? theme.palette.text.secondary : 'rgba(255,255,255,0.7)';
  const sidebarDivider = isDark ? theme.palette.divider : 'rgba(255,255,255,0.1)';
  const sidebarHover = isDark ? theme.palette.action.hover : 'rgba(255,255,255,0.08)';
  const sidebarActive = isDark ? `${theme.palette.primary.main}20` : 'rgba(255,255,255,0.15)';

  // Get current nav item
  const currentNav = navItems.find(item => location.pathname.startsWith(item.path))?.id || 'dashboard';

  // Get user initials
  const getInitials = () => {
    if (profile) {
      const first = profile.first_name?.[0] || '';
      const last = profile.last_name?.[0] || '';
      return (first + last).toUpperCase() || 'DR';
    }
    return 'DR';
  };

  const getUserName = () => {
    if (profile) {
      return `Dr. ${profile.first_name || ''} ${profile.last_name || ''}`.trim() || 'Doctor';
    }
    return 'Doctor';
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    setMobileDrawerOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    sessionStorage.clear();
    navigate('/login');
  };

  // Sidebar Content
  const SidebarContent = () => (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      bgcolor: sidebarBg,
      color: sidebarText,
      transition: 'background-color 0.3s ease, color 0.3s ease',
    }}>
      {/* Logo Header */}
      <Box sx={{ 
        p: 2.5, 
        display: 'flex', 
        alignItems: 'center', 
        gap: 1.5,
        borderBottom: `1px solid ${sidebarDivider}`,
      }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            bgcolor: isDark ? theme.palette.primary.main : 'rgba(255,255,255,0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: isDark ? 'white' : 'white',
            boxShadow: isDark ? `0 4px 12px ${theme.palette.primary.main}40` : 'none',
          }}
        >
          <Activity size={24} />
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography 
            variant="h6" 
            fontWeight={700}
            sx={{ lineHeight: 1.2, color: sidebarText }}
          >
            OncoLife
          </Typography>
          <Typography 
            variant="caption"
            sx={{ 
              display: 'block', 
              lineHeight: 1.2,
              color: sidebarTextMuted,
            }}
          >
            Physician Portal
          </Typography>
        </Box>
        {isMobile && (
          <IconButton 
            onClick={() => setMobileDrawerOpen(false)}
            sx={{ color: sidebarText }}
          >
            <X size={20} />
          </IconButton>
        )}
      </Box>

      {/* User Profile Section */}
      <Box sx={{ 
        p: 2, 
        display: 'flex', 
        alignItems: 'center', 
        gap: 1.5,
        borderBottom: `1px solid ${sidebarDivider}`,
      }}>
        <Avatar 
          sx={{ 
            bgcolor: theme.palette.secondary.main,
            width: 44,
            height: 44,
            fontWeight: 600,
          }}
        >
          {getInitials()}
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography 
            variant="body2" 
            sx={{ color: sidebarTextMuted }}
          >
            Welcome
          </Typography>
          <Typography 
            variant="body1" 
            fontWeight={600}
            sx={{ 
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              color: sidebarText,
            }}
          >
            {getUserName()}
          </Typography>
        </Box>
      </Box>

      {/* Navigation Links */}
      <Box sx={{ flex: 1, py: 2, overflow: 'auto' }}>
        <Typography 
          variant="overline"
          sx={{ 
            px: 2, 
            mb: 1, 
            display: 'block',
            color: sidebarTextMuted,
            fontSize: '0.7rem',
            letterSpacing: '0.1em',
            opacity: 0.7,
          }}
        >
          Navigation
        </Typography>
        <List disablePadding>
          {navItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = currentNav === item.id;
            return (
              <ListItem 
                key={item.id} 
                disablePadding
                sx={{
                  animation: 'slideInLeft 0.3s ease-out forwards',
                  animationDelay: `${index * 50}ms`,
                  opacity: 0,
                  '@keyframes slideInLeft': {
                    '0%': { opacity: 0, transform: 'translateX(-20px)' },
                    '100%': { opacity: 1, transform: 'translateX(0)' },
                  },
                }}
              >
                <ListItemButton
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    mx: 1,
                    borderRadius: 2,
                    bgcolor: isActive ? sidebarActive : 'transparent',
                    color: sidebarText,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: isActive 
                        ? (isDark ? `${theme.palette.primary.main}30` : 'rgba(255,255,255,0.2)')
                        : sidebarHover,
                    },
                  }}
                >
                  <ListItemIcon sx={{ 
                    minWidth: 40,
                    color: isActive 
                      ? (isDark ? theme.palette.primary.main : 'white') 
                      : sidebarTextMuted,
                  }}>
                    <Icon size={22} />
                  </ListItemIcon>
                  <ListItemText 
                    primary={item.label}
                    primaryTypographyProps={{
                      fontWeight: isActive ? 600 : 500,
                      color: 'inherit',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* Theme Toggle & Logout */}
      <Box sx={{ borderTop: `1px solid ${sidebarDivider}` }}>
        <Box sx={{ p: 1.5 }}>
          {/* Dark Mode Toggle */}
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            px: 1.5,
            py: 1,
            mb: 1,
          }}>
            <Typography variant="body2" sx={{ color: sidebarTextMuted }}>
              {isDark ? 'Dark Mode' : 'Light Mode'}
            </Typography>
            <DarkModeToggle variant="pill" />
          </Box>
          
          {/* Logout */}
          <ListItemButton
            onClick={handleLogout}
            sx={{
              borderRadius: 2,
              color: isDark ? theme.palette.error.main : '#FCA5A5',
              transition: 'all 0.2s ease',
              '&:hover': {
                bgcolor: isDark ? `${theme.palette.error.main}15` : 'rgba(239, 68, 68, 0.15)',
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
              <LogOut size={22} />
            </ListItemIcon>
            <ListItemText primary="Log out" />
          </ListItemButton>
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Desktop Sidebar */}
      {!isMobile && (
        <Drawer
          variant="permanent"
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
              border: 'none',
              transition: 'background-color 0.3s ease',
            },
          }}
        >
          <SidebarContent />
        </Drawer>
      )}

      {/* Mobile Drawer */}
      <Drawer
        variant="temporary"
        open={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            width: 280,
            boxSizing: 'border-box',
          },
        }}
      >
        <SidebarContent />
      </Drawer>

      {/* Main Content Area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          bgcolor: 'background.default',
          transition: 'background-color 0.3s ease',
        }}
      >
        {/* Mobile Header */}
        {isMobile && (
          <AppBar 
            position="sticky" 
            elevation={0}
            sx={{ 
              bgcolor: isDark ? 'background.paper' : theme.palette.primary.main,
              borderBottom: isDark ? `1px solid ${theme.palette.divider}` : 'none',
              transition: 'all 0.3s ease',
            }}
          >
            <Toolbar sx={{ minHeight: { xs: 56 } }}>
              <IconButton
                edge="start"
                onClick={() => setMobileDrawerOpen(true)}
                sx={{ mr: 1, color: isDark ? 'text.primary' : 'white' }}
              >
                <MenuIcon />
              </IconButton>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Activity size={24} color={isDark ? theme.palette.primary.main : 'white'} />
                <Typography 
                  variant="h6" 
                  fontWeight={700} 
                  sx={{ color: isDark ? 'text.primary' : 'white' }}
                >
                  OncoLife
                </Typography>
              </Box>
              <Box sx={{ flexGrow: 1 }} />
              <DarkModeToggle variant="icon" size="small" />
              <Avatar 
                sx={{ 
                  width: 36, 
                  height: 36,
                  bgcolor: theme.palette.secondary.main,
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  ml: 0.5,
                }}
              >
                {getInitials()}
              </Avatar>
            </Toolbar>
          </AppBar>
        )}

        {/* Page Content with animation */}
        <Box 
          sx={{ 
            flex: 1, 
            overflow: 'auto',
            animation: 'fadeIn 0.3s ease-out',
            '@keyframes fadeIn': {
              '0%': { opacity: 0 },
              '100%': { opacity: 1 },
            },
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default Layout;
