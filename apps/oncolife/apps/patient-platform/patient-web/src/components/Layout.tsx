/**
 * OncoLife Ruby - Patient Layout
 * 
 * Responsive layout with:
 * - Desktop: Sidebar navigation
 * - Mobile: Bottom tab navigation
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
import BottomNavigation from '@mui/material/BottomNavigation';
import BottomNavigationAction from '@mui/material/BottomNavigationAction';
import Avatar from '@mui/material/Avatar';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import Paper from '@mui/material/Paper';
import { 
  MessageCircle, 
  FileText, 
  BookOpen, 
  GraduationCap, 
  User,
  Menu as MenuIcon,
  LogOut,
  X,
  MessageCircleQuestion
} from 'lucide-react';
import { DarkModeToggle, useThemeMode } from '@oncolife/ui-components';

// Sidebar width
const DRAWER_WIDTH = 260;

// Navigation items
const navItems = [
  { id: 'chat', label: 'Symptom Check', icon: MessageCircle, path: '/chat' },
  { id: 'summaries', label: 'Summaries', icon: FileText, path: '/summaries' },
  { id: 'notes', label: 'Diary', icon: BookOpen, path: '/notes' },
  { id: 'questions', label: 'Questions', icon: MessageCircleQuestion, path: '/questions' },
  { id: 'education', label: 'Education', icon: GraduationCap, path: '/education' },
  { id: 'profile', label: 'Profile', icon: User, path: '/profile' },
];

const Layout: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { isDark } = useThemeMode();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Get current nav item
  const currentNav = navItems.find(item => location.pathname.startsWith(item.path))?.id || 'chat';

  const handleNavigation = (path: string) => {
    navigate(path);
    setMobileDrawerOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    sessionStorage.clear();
    navigate('/login');
  };

  // Desktop Sidebar Content
  const SidebarContent = () => (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      bgcolor: 'background.paper',
      transition: 'background-color 0.3s ease',
    }}>
      {/* Logo Header */}
      <Box sx={{ 
        p: 2, 
        display: 'flex', 
        alignItems: 'center', 
        gap: 1.5,
        borderBottom: `1px solid ${theme.palette.divider}`,
      }}>
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '1.25rem',
            boxShadow: `0 4px 12px ${theme.palette.primary.main}40`,
          }}
        >
          💎
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography 
            variant="subtitle1" 
            fontWeight={700} 
            color="primary"
            sx={{ lineHeight: 1.2 }}
          >
            OncoLife
          </Typography>
          <Typography 
            variant="caption" 
            color="text.secondary"
            sx={{ display: 'block', lineHeight: 1.2 }}
          >
            Ruby
          </Typography>
        </Box>
        {isMobile && (
          <IconButton 
            onClick={() => setMobileDrawerOpen(false)}
            sx={{ ml: 'auto' }}
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
        borderBottom: `1px solid ${theme.palette.divider}`,
        cursor: 'pointer',
        transition: 'background-color 0.2s ease',
        '&:hover': { bgcolor: theme.palette.action.hover },
      }}
      onClick={() => handleNavigation('/profile')}
      >
        <Avatar 
          sx={{ 
            background: `linear-gradient(135deg, ${theme.palette.secondary.main} 0%, ${theme.palette.secondary.dark} 100%)`,
            width: 44,
            height: 44,
          }}
        >
          U
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" color="text.secondary">
            Welcome back
          </Typography>
          <Typography 
            variant="body1" 
            fontWeight={600}
            sx={{ 
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            Patient
          </Typography>
        </Box>
      </Box>

      {/* Navigation Links */}
      <Box sx={{ flex: 1, py: 2, overflow: 'auto' }}>
        <Typography 
          variant="overline" 
          color="text.secondary"
          sx={{ px: 2, mb: 1, display: 'block' }}
        >
          Menu
        </Typography>
        <List disablePadding>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentNav === item.id;
            return (
              <ListItem key={item.id} disablePadding>
                <ListItemButton
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    mx: 1,
                    borderRadius: 2,
                    bgcolor: isActive ? `${theme.palette.primary.main}15` : 'transparent',
                    color: isActive ? theme.palette.primary.main : theme.palette.text.primary,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: isActive 
                        ? `${theme.palette.primary.main}20` 
                        : theme.palette.action.hover,
                    },
                  }}
                >
                  <ListItemIcon sx={{ 
                    minWidth: 40,
                    color: isActive ? theme.palette.primary.main : theme.palette.text.secondary,
                  }}>
                    <Icon size={22} />
                  </ListItemIcon>
                  <ListItemText 
                    primary={item.label}
                    primaryTypographyProps={{
                      fontWeight: isActive ? 600 : 500,
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* Theme Toggle & Logout */}
      <Divider />
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
          <Typography variant="body2" color="text.secondary">
            {isDark ? 'Dark Mode' : 'Light Mode'}
          </Typography>
          <DarkModeToggle variant="pill" />
        </Box>
        
        {/* Logout */}
        <ListItemButton
          onClick={handleLogout}
          sx={{
            borderRadius: 2,
            color: theme.palette.error.main,
            transition: 'all 0.2s ease',
            '&:hover': {
              bgcolor: `${theme.palette.error.main}10`,
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
              borderRight: `1px solid ${theme.palette.divider}`,
              transition: 'background-color 0.3s ease, border-color 0.3s ease',
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
          pb: isMobile ? '64px' : 0, // Space for bottom nav
        }}
      >
        {/* Mobile Header */}
        {isMobile && (
          <AppBar 
            position="sticky" 
            color="inherit" 
            elevation={0}
            sx={{ 
              borderBottom: `1px solid ${theme.palette.divider}`,
              bgcolor: 'background.paper',
              transition: 'all 0.3s ease',
            }}
          >
            <Toolbar sx={{ minHeight: { xs: 56 } }}>
              <IconButton
                edge="start"
                onClick={() => setMobileDrawerOpen(true)}
                sx={{ mr: 1 }}
              >
                <MenuIcon />
              </IconButton>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    borderRadius: 1.5,
                    background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1rem',
                  }}
                >
                  💎
                </Box>
                <Typography variant="h6" fontWeight={700} color="primary">
                  OncoLife
                </Typography>
              </Box>
              <Box sx={{ flexGrow: 1 }} />
              <DarkModeToggle variant="icon" size="small" />
              <IconButton onClick={() => handleNavigation('/profile')} sx={{ ml: 0.5 }}>
                <Avatar 
                  sx={{ 
                    width: 32, 
                    height: 32,
                    background: `linear-gradient(135deg, ${theme.palette.secondary.main} 0%, ${theme.palette.secondary.dark} 100%)`,
                    fontSize: '0.875rem',
                  }}
                >
                  U
                </Avatar>
              </IconButton>
            </Toolbar>
          </AppBar>
        )}

        {/* Page Content with animation */}
        <Box 
          sx={{ 
            flex: 1, 
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0, /* Important: allows flex child to shrink below content size */
            animation: 'fadeIn 0.3s ease-out',
            '@keyframes fadeIn': {
              '0%': { opacity: 0 },
              '100%': { opacity: 1 },
            },
          }}
        >
          <Outlet />
        </Box>

        {/* Mobile Bottom Navigation */}
        {isMobile && (
          <Paper 
            elevation={8}
            sx={{ 
              position: 'fixed', 
              bottom: 0, 
              left: 0, 
              right: 0,
              zIndex: theme.zIndex.appBar,
              borderTop: `1px solid ${theme.palette.divider}`,
              bgcolor: 'background.paper',
              transition: 'all 0.3s ease',
              // Safe area for iOS
              pb: 'env(safe-area-inset-bottom)',
            }}
          >
            <BottomNavigation
              value={currentNav}
              onChange={(_, newValue) => {
                const item = navItems.find(i => i.id === newValue);
                if (item) handleNavigation(item.path);
              }}
              showLabels
              sx={{ height: 64, bgcolor: 'transparent' }}
            >
              {navItems.slice(0, 4).map((item) => {
                const Icon = item.icon;
                return (
                  <BottomNavigationAction
                    key={item.id}
                    label={item.label}
                    value={item.id}
                    icon={<Icon size={24} />}
                    sx={{
                      minWidth: 60,
                      '&.Mui-selected': {
                        color: theme.palette.primary.main,
                      },
                      transition: 'color 0.2s ease',
                    }}
                  />
                );
              })}
            </BottomNavigation>
          </Paper>
        )}
      </Box>
    </Box>
  );
};

export default Layout;
