// src/App.js

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './Pages/DashboardPage';
import ExpensesPage from './Pages/ExpensesPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="expenses" element={<ExpensesPage />} />
      </Route>
    </Routes>
  );
}

export default App;