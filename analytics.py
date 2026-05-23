import pandas as pd
import numpy as np

def calculate_task_analytics(tasks):
    """
    Given a list of Task objects or dictionaries, load them into a
    Pandas DataFrame and calculate:
    - Total Tasks
    - Completed Tasks
    - Pending Tasks
    - Completion Percentage
    """
    defaults = {
        'total_tasks': 0,
        'completed_tasks': 0,
        'pending_tasks': 0,
        'completion_percentage': 0.0
    }
    
    if not tasks:
        return defaults

    # Convert tasks to a list of dicts if they are SQLAlchemy model objects
    task_dicts = []
    for t in tasks:
        if hasattr(t, 'to_dict'):
            task_dicts.append(t.to_dict())
        elif isinstance(t, dict):
            task_dicts.append(t)
            
    if not task_dicts:
        return defaults

    # Create a Pandas DataFrame from the tasks data
    df = pd.DataFrame(task_dicts)
    
    # Check if 'status' column exists in DataFrame
    if 'status' not in df.columns:
        return defaults
    
    # 1. Total Tasks
    total_tasks = int(df.shape[0])
    
    # Convert 'status' column values to numpy array for operations
    status_array = df['status'].to_numpy()
    
    # 2. Completed Tasks (using NumPy array logic)
    completed_mask = (status_array == 'Completed')
    completed_tasks = int(np.sum(completed_mask))
    
    # 3. Pending Tasks (using NumPy array logic)
    pending_mask = (status_array == 'Pending')
    pending_tasks = int(np.sum(pending_mask))
    
    # 4. Completion Percentage (using NumPy rounding)
    if total_tasks > 0:
        completion_percentage = float(np.round((completed_tasks / total_tasks) * 100, 2))
    else:
        completion_percentage = 0.0
        
    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'completion_percentage': completion_percentage
    }
