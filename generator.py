import random

class Satellite:
    def __init__(self, id, t_start_s, t_end_s, capacity, transition_time):
        self.id = id
        self.t_start_s = t_start_s
        self.t_end_s = t_end_s
        self.capacity = capacity
        self.transition_time = transition_time

    @staticmethod
    def generate(i):
        t_start_s = random.uniform(0, 100)
        t_end_s = t_start_s + random.uniform(0, 300 - t_start_s)
        capacity = random.randint(1, 10)
        transition_time = 1

        return Satellite(
            id=f"satellite_{i+1}",
            t_start_s=t_start_s,
            t_end_s=t_end_s,
            capacity=capacity,
            transition_time=transition_time
        )

class User:
    def __init__(self, id, priority, exclusive_windows=None, satellite=None):
        self.id = id
        self.priority = priority
        self.exclusive_windows = exclusive_windows if exclusive_windows else []
        self.satellite = satellite

    @staticmethod
    def generate_exclusive_users(num_exclusive_users, satellites, total_time=300):
        exclusive_windows_all_users = []
        users = []
        available_priorities = list(range(1, num_exclusive_users + 2))  # +2 pour inclure le planificateur central

        if num_exclusive_users > len(satellites):
            raise ValueError("Il n'y a pas assez de satellites pour le nombre d'utilisateurs exclusifs")

        exclusive_satellites = random.sample(satellites, num_exclusive_users)

        for i, satellite in enumerate(exclusive_satellites, start=1):
            exclusive_windows = generate_exclusive_windows(8, (15, 20), total_time, exclusive_windows_all_users)
            exclusive_windows_all_users.extend(exclusive_windows)
            priority = random.choice(available_priorities)
            available_priorities.remove(priority)
            windows_for_user = [(satellite.id, start, end) for start, end in exclusive_windows]
            users.append(User(
                id=f"exclusive_user_{i}",
                priority=priority,
                exclusive_windows=windows_for_user,
                satellite=satellite.id
            ))

        # Ajouter le planificateur central
        central_planner_priority = available_priorities[0]
        users.append(User(
            id="central_planner",
            priority=central_planner_priority,
            satellite=None
        ))

        return users

def generate_exclusive_windows(num_windows, window_length_range, total_time, existing_windows):
    windows = []
    while len(windows) < num_windows:
        start = random.uniform(0, total_time - window_length_range[1])
        end = start + random.uniform(*window_length_range)
        if not any(existing_start <= start < existing_end or existing_start < end <= existing_end for existing_start, existing_end in existing_windows + windows):
            windows.append((start, end))
    return windows

class ObservationOpportunity:
    def __init__(self, t_start_o, t_end_o, duration, reward, satellite, user):
        self.t_start_o = t_start_o
        self.t_end_o = t_end_o
        self.duration = duration
        self.reward = reward
        self.satellite = satellite
        self.user = user

    @staticmethod
    def generate(request, satellite, time_window_length):
        t_start_o = random.uniform(request.t_start_r, request.t_end_r - time_window_length)
        t_end_o = t_start_o + time_window_length

        return ObservationOpportunity(
            t_start_o=t_start_o,
            t_end_o=t_end_o,
            duration=request.duration,
            reward=request.reward,
            satellite=satellite,
            user=request.user
        )

class Task:
    def __init__(self, id, t_start_r, t_end_r, duration, reward, gps_position, user, observation_opportunities):
        self.id = id
        self.t_start_r = t_start_r
        self.t_end_r = t_end_r
        self.duration = duration
        self.reward = reward
        self.gps_position = gps_position
        self.user = user
        self.observation_opportunities = observation_opportunities

    @staticmethod
    def generate(task_id, user, satellites, request_time_window=(0, 300)):
        t_start_r = random.uniform(*request_time_window)
        t_end_r = t_start_r + random.uniform(10, 20)
        duration = 5
        reward = random.randint(10, 50) if user.priority >= 10 else random.randint(1, 5)
        
        # Générer une position GPS en format LLA (Latitude, Longitude, Altitude)
        latitude = random.uniform(-90, 90)
        longitude = random.uniform(-180, 180)
        altitude = random.uniform(0, 400)  # altitude en kilomètres
        gps_position = (latitude, longitude, altitude)

        satellite_for_observation = user.satellite if user.satellite else random.choice(satellites)

        # Créer l'objet Task avant de générer les opportunités d'observation
        new_task = Task(
            id=f"task_{task_id}",
            t_start_r=t_start_r,
            t_end_r=t_end_r,
            duration=duration,
            reward=reward,
            gps_position=gps_position,
            user=user,
            observation_opportunities=[]
        )

        # Générer les opportunités d'observation pour cette tâche
        new_task.observation_opportunities = [
            ObservationOpportunity.generate(
                new_task,
                satellite_for_observation,
                duration
            ) for _ in range(10)
        ]

        return new_task

class Instance:
    def __init__(self, satellites, users, tasks):
        self.satellites = satellites
        self.users = users
        self.tasks = tasks

    @staticmethod
    def generate(num_satellites, num_exclusive_users, num_tasks_per_user):
        satellites = [Satellite.generate(i) for i in range(num_satellites)]
        users = User.generate_exclusive_users(num_exclusive_users, satellites)

        tasks = []
        task_id = 1
        for user in users:
            num_user_requests = num_tasks_per_user if user.exclusive_windows else random.randint(8, 80)
            for _ in range(num_user_requests):
                task = Task.generate(task_id, user, satellites)
                tasks.append(task)
                task_id += 1

        return Instance(satellites, users, tasks)
    
    def format_for_display(self):
        formatted_output = "EOSCSP Instance:\n\n"

        # Affichage des satellites
        formatted_output += "Satellites:\n"
        for sat in self.satellites:
            formatted_output += f"  ID: {sat.id}, Start: {sat.t_start_s}, End: {sat.t_end_s}, Capacity: {sat.capacity}, Transition Time: {sat.transition_time}\n"
        
        # Affichage des utilisateurs
        formatted_output += "\nUsers:\n"
        for user in self.users:
            formatted_output += f"  ID: {user.id}, Priority: {user.priority}, Exclusive Windows: {user.exclusive_windows}\n"
        
        # Affichage des tâches
        formatted_output += "\nTasks:\n"
        for task in self.tasks:
            formatted_output += f"  ID: {task.id}, Start: {task.t_start_r}, End: {task.t_end_r}, Duration: {task.duration}, Reward: {task.reward}, GPS Position: {task.gps_position}, User: {task.user.id}\n"
            formatted_output += "    Observation Opportunities:\n"
            for opp in task.observation_opportunities:
                formatted_output += f"      Satellite: {opp.satellite}, Start: {opp.t_start_o}, End: {opp.t_end_o}, Duration: {opp.duration}, Reward: {opp.reward}\n"

        return formatted_output
    
# Créer une instance EOSCSP
eoscp_instance = Instance.generate(num_satellites=5, num_exclusive_users=4, num_tasks_per_user=20)

# Afficher l'instance formatée
print(eoscp_instance.format_for_display())
