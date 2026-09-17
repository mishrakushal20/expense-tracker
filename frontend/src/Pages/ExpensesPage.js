import React, { useEffect, useState } from 'react';
import {
  AppBar, Toolbar, Typography, Container, Grid, Card, CardContent, CardActions, IconButton, Button, Box, CircularProgress, Tooltip, Dialog, DialogTitle, DialogContent, TextField, DialogActions
} from '@mui/material'; // Yahan se DialogContentText hata diya gaya hai
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import FastfoodIcon from '@mui/icons-material/Fastfood';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import CommuteIcon from '@mui/icons-material/Commute';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import '../App.css';
// CSRF Token lene ke liye ek helper function
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

// Category ke hisaab se icon dega
const getCategoryIcon = (category) => {
  switch (category?.toLowerCase()) {
    case 'food': return <FastfoodIcon color="secondary" />;
    case 'shopping': return <ShoppingCartIcon color="primary" />;
    case 'travel': return <CommuteIcon color="success" />;
    default: return <AttachMoneyIcon color="action" />;
  }
};

// Date ko format karne ke liye naya function
const formatDate = (dateString) => {
    const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-GB', options);
};

function App() {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [currentExpense, setCurrentExpense] = useState(null);

  const fetchExpenses = () => {
    setLoading(true);
    fetch('http://localhost:8000/api/expenses/', { credentials: 'include' })
      .then(response => {
        if (response.status === 401 || response.status === 403) {
          window.location.href = 'http://localhost:8000/authentication/login';
          return null;
        }
        return response.json();
      })
      .then(data => {
        if (data) {
          setExpenses(data);
        }
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching expenses:', error);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchExpenses();
  }, []);

  const handleAddClickOpen = () => setAddOpen(true);
  const handleAddClose = () => setAddOpen(false);

  const handleEditClickOpen = (expense) => {
    setCurrentExpense(expense);
    setEditOpen(true);
  };
  const handleEditClose = () => {
    setEditOpen(false);
    setCurrentExpense(null);
  };
  
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    if (currentExpense) {
      setCurrentExpense({ ...currentExpense, [name]: value });
    }
  };

  const handleUpdate = () => {
    if (!currentExpense) return;
    fetch(`http://localhost:8000/api/expenses/${currentExpense.id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        credentials: 'include',
        body: JSON.stringify({ ...currentExpense, amount: parseFloat(currentExpense.amount) }),
    })
    .then(response => { if (!response.ok) throw new Error('Update failed'); return response.json(); })
    .then(() => { fetchExpenses(); handleEditClose(); })
    .catch((error) => console.error('Error updating expense:', error));
  };

  const handleDelete = (id) => {
    fetch(`http://localhost:8000/api/expenses/${id}/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrftoken },
        credentials: 'include',
    })
    .then(response => { if (!response.ok) throw new Error('Delete failed'); fetchExpenses(); })
    .catch((error) => console.error('Error deleting expense:', error));
  };

  const [newExpenseData, setNewExpenseData] = useState({ amount: '', description: '', category: '', date: new Date().toISOString().slice(0, 10) });
  const handleAddInputChange = (e) => {
    const { name, value } = e.target;
    setNewExpenseData({ ...newExpenseData, [name]: value });
  };
  const handleSubmit = () => {
    fetch('http://localhost:8000/api/expenses/create/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        credentials: 'include',
        body: JSON.stringify({ ...newExpenseData, amount: parseFloat(newExpenseData.amount) }),
    })
    .then(response => { if (!response.ok) throw new Error('Create failed'); return response.json(); })
    .then(() => { fetchExpenses(); handleAddClose(); })
    .catch((error) => console.error('Error creating expense:', error));
  };

  return (
    <Box sx={{ backgroundColor: '#f4f6f8', minHeight: '100vh', pb: 4 }}>
      <AppBar position="sticky">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>ExpenseWise</Typography>
        </Toolbar>
      </AppBar>
      <Container sx={{ marginTop: '2rem' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>My Expenses</Typography>
            <Button variant="contained" startIcon={<AddIcon />} sx={{ borderRadius: '16px', boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)' }} onClick={handleAddClickOpen}>
              Add Expense
            </Button>
        </Box>
        
        {loading ? ( <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}><CircularProgress /></Box> ) : (
            <Grid container spacing={3}>
              {expenses.map((expense) => (
                <Grid item xs={12} sm={6} md={4} key={expense.id}>
                  <Card elevation={2} sx={{ borderRadius: '12px', transition: 'transform 0.2s', '&:hover': { transform: 'translateY(-5px)', boxShadow: 6 }, display: 'flex', flexDirection: 'column', height: '100%' }}>
                    <CardContent sx={{ flexGrow: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        {getCategoryIcon(expense.category)}
                        <Typography variant="h6" component="div" sx={{ ml: 1.5, fontWeight: 'medium' }}>{expense.category}</Typography>
                      </Box>
                      <Typography variant="body1" sx={{ minHeight: '48px' }}>{expense.description}</Typography>
                      <Typography variant="h5" color="text.primary" sx={{ fontWeight: 'bold', textAlign: 'right', mt: 2 }}>
                        ₹{expense.amount.toFixed(2)}
                      </Typography>
                    </CardContent>
                    <CardActions sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', px: 2, pb: 2 }}>
                      <Typography sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                        {formatDate(expense.date)}
                      </Typography>
                      <Box>
                        <Tooltip title="Edit Expense"><IconButton size="small" color="primary" onClick={() => handleEditClickOpen(expense)}><EditIcon /></IconButton></Tooltip>
                        <Tooltip title="Delete Expense"><IconButton size="small" color="error" onClick={() => handleDelete(expense.id)}><DeleteIcon /></IconButton></Tooltip>
                      </Box>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
        )}
      </Container>

      {/* Add Expense Dialog */}
      <Dialog open={addOpen} onClose={handleAddClose}>
        <DialogTitle>Add a New Expense</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" name="amount" label="Amount" type="number" fullWidth variant="standard" onChange={handleAddInputChange} />
          <TextField margin="dense" name="description" label="Description" type="text" fullWidth variant="standard" onChange={handleAddInputChange} />
          <TextField margin="dense" name="category" label="Category" type="text" fullWidth variant="standard" onChange={handleAddInputChange} />
          <TextField margin="dense" name="date" label="Date" type="date" fullWidth variant="standard" defaultValue={newExpenseData.date} onChange={handleAddInputChange} />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleAddClose}>Cancel</Button>
          <Button onClick={handleSubmit}>Save</Button>
        </DialogActions>
      </Dialog>
      
      {/* Edit Expense Dialog */}
      <Dialog open={editOpen} onClose={handleEditClose}>
        <DialogTitle>Edit Expense</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" name="amount" label="Amount" type="number" fullWidth variant="standard" value={currentExpense?.amount || ''} onChange={handleInputChange} />
          <TextField margin="dense" name="description" label="Description" type="text" fullWidth variant="standard" value={currentExpense?.description || ''} onChange={handleInputChange} />
          <TextField margin="dense" name="category" label="Category" type="text" fullWidth variant="standard" value={currentExpense?.category || ''} onChange={handleInputChange} />
          <TextField margin="dense" name="date" label="Date" type="date" fullWidth variant="standard" value={currentExpense?.date || ''} onChange={handleInputChange} />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleEditClose}>Cancel</Button>
          <Button onClick={handleUpdate}>Update</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default App;