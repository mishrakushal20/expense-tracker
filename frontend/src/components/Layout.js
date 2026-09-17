// src/components/Layout.js

import React from 'react';
import Navbar from './Navbar';
import { Outlet } from 'react-router-dom';
import CssBaseline from '@mui/material/CssBaseline';

function Layout() {
  return (
    <div>
      <CssBaseline />
      <Navbar />
      <main style={{ padding: '20px' }}>
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;