from django.shortcuts import render, redirect, get_object_or_404
from .models import Goal
from .forms import GoalForm, AddAmountForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail

@login_required(login_url='/authentication/login')
def add_goal(request):
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            # FIX: Use commit=False to add the owner before saving.
            goal = form.save(commit=False)
            goal.owner = request.user
            goal.save()
            messages.success(request, 'Goal added successfully!')
            return redirect('list_goals')
    else:
        form = GoalForm()
    return render(request, 'goals/add_goal.html', {'form': form})

@login_required(login_url='/authentication/login')
def list_goals(request):
    goals = Goal.objects.filter(owner=request.user).order_by('end_date')
    add_amount_form = AddAmountForm() 
    return render(request, 'goals/list_goals.html', {'goals': goals, 'add_amount_form': add_amount_form})

@login_required(login_url='/authentication/login')
def add_amount(request, goal_id):
    # FIX: Security vulnerability patched. Ensures user can only affect their own goals.
    goal = get_object_or_404(Goal, pk=goal_id, owner=request.user)

    if request.method == 'POST':
        form = AddAmountForm(request.POST)
        if form.is_valid():
            additional_amount = form.cleaned_data['additional_amount']
            amount_required = goal.amount_to_save - goal.current_saved_amount

            if additional_amount > amount_required:
                messages.error(request, f'The amount cannot be more than the remaining {amount_required}.')
            else:
                goal.current_saved_amount += additional_amount
                goal.save()

                if goal.current_saved_amount >= goal.amount_to_save:
                    send_congratulatory_email(request.user.email, goal)
                    messages.success(request, f'Congratulations! You have achieved your goal: "{goal.name}"')
                    goal.delete() # Deleting the goal once completed
                else:
                    messages.success(request, f'Amount added successfully.')
    
    return redirect('list_goals')

def send_congratulatory_email(email, goal):
    subject = 'Congratulations on Achieving Your Goal!'
    message = f'Dear User,\n\nCongratulations on achieving your goal "{goal.name}". You have successfully saved {goal.amount_to_save}.\n\nKeep up the good work!\n\nBest regards,\nThe ExpenseWise Team'
    
    # NOTE: Replace 'from@example.com' with your actual sender email from settings.py
    send_mail(subject, message, 'from@example.com', [email])

@login_required(login_url='/authentication/login')
def delete_goal(request, goal_id):
    # This view is already correct and secure, well done!
    goal = get_object_or_404(Goal, id=goal_id, owner=request.user)
    goal.delete()
    messages.success(request, 'Goal deleted.')
    return redirect('list_goals')