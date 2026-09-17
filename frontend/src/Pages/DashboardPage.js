import React from 'react';
import { Typography, Box, AppBar, Toolbar } from '@mui/material';
import { Link } from 'react-router-dom'; // Step 1: Link ko import karein
import '../App.css'; 

function DashboardPage() {
  return (
    <div>
      {/* Aapka purana header/dashboard code yahan ho sakta hai */}
      <h1>Smart Dashboard</h1>
      <p>Yahan hum apne sundar charts aur graphs banayenge.</p>

      <hr />

      {/* Step 2: Link component ka istemaal karein */}
      <Link to="/expenses">
    
      </Link>
    </div>
  );
}

export default DashboardPage;