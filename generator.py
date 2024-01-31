from asyncio import tasks
import random
import time

random.seed(time.time())

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
        capacity = 20
        transition_time = 1

        return Satellite(
            id=f"satellite_{i+1}",
            t_start_s=t_start_s,
            t_end_s=t_end_s,
            capacity=capacity,
            transition_time=transition_time
        )

class User:
    def __init__(self, id, priority, exclusive_windows=None):
        self.id = id
        self.priority = priority
        self.exclusive_windows = exclusive_windows if exclusive_windows else []

    @staticmethod
    def generate_exclusive_users(num_exclusive_users, satellites, total_time=300):
        exclusive_windows_all_users = []
        users = []
        available_priorities = list(range(1, num_exclusive_users + 2))
        used_satellites = set()

        for i in range(1, num_exclusive_users + 1):
            priority = random.choice(available_priorities)
            available_priorities.remove(priority)
            exclusive_windows = []
            for satellite in random.sample(satellites, random.randint(1, len(satellites))):
                if satellite.id not in used_satellites:
                    windows = generate_exclusive_windows(8, (15, 20), total_time, exclusive_windows_all_users)
                    if windows:
                        exclusive_windows.extend([(satellite.id, start, end) for start, end in windows])
                        exclusive_windows_all_users.extend(windows)
                        used_satellites.add(satellite.id)
            users.append(User(
                id=f"exclusive_user_{i}",
                priority=priority,
                exclusive_windows=exclusive_windows
            ))

        # Ajouter le planificateur central
        central_planner_priority = available_priorities[0]
        users.append(User(
            id="central_planner",
            priority=central_planner_priority
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
    _id_counter = 0  # Compteur de classe pour générer des ID uniques

    def __init__(self, t_start_o, t_end_o, duration_o, request_o, reward_o, satellite_o, user_o, priority_o):
        self.id = ObservationOpportunity._generate_id()  # Générer un ID unique pour chaque instance
        self.t_start_o = t_start_o
        self.t_end_o = t_end_o
        self.duration_o = duration_o
        self.request_o = request_o
        self.reward_o = reward_o
        self.satellite_o = satellite_o
        self.user_o = user_o
        self.priority_o = priority_o

    @staticmethod
    def _generate_id():
        ObservationOpportunity._id_counter += 1
        return f"obs_{ObservationOpportunity._id_counter}"

    @staticmethod
    def generate(request, satellite, time_window_length):
        t_start_o = random.uniform(request.t_start_r, request.t_end_r - time_window_length)
        t_end_o = t_start_o + time_window_length

        return ObservationOpportunity(
            t_start_o=t_start_o,
            t_end_o=t_end_o,
            duration_o=request.duration, # Assuming duration of request is the duration of observation
            request_o=request,
            reward_o=request.reward, # Assuming reward for observation is the reward for the request
            satellite_o=satellite,
            user_o=request.user,
            priority_o=request.user.priority
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
        latitude, longitude, altitude = generate_gps_position()

        satellite_ids = [window[0] for window in user.exclusive_windows] if user.exclusive_windows else []
        satellite_for_observation = random.choice([sat for sat in satellites if sat.id in satellite_ids]) if satellite_ids else random.choice(satellites)

        new_task = Task(
            id=f"task_{task_id}",
            t_start_r=t_start_r,
            t_end_r=t_end_r,
            duration=duration,
            reward=reward,
            gps_position=(latitude, longitude, altitude),
            user=user,
            observation_opportunities=[]
        )

        for _ in range(10):
            new_task.observation_opportunities.append(
                ObservationOpportunity.generate(new_task, satellite_for_observation, duration)
            )

        return new_task

def generate_gps_position():
    latitude = random.uniform(-90, 90)
    longitude = random.uniform(-180, 180)
    altitude = random.uniform(0, 400)
    return latitude, longitude, altitude

class Instance:
    def __init__(self, satellites, users, tasks, observation_opportunities):
        self.satellites = satellites
        self.users = users
        self.tasks = tasks
        self.observation_opportunities = observation_opportunities

    @staticmethod
    def generate(num_satellites, num_exclusive_users, num_tasks_per_user):
        satellites = [Satellite.generate(i) for i in range(num_satellites)]
        users = User.generate_exclusive_users(num_exclusive_users, satellites)

        tasks = []
        all_observation_opportunities = []
        task_id = 1
        for user in users:
            num_user_requests = num_tasks_per_user if user.id.startswith("exclusive_user_") else random.randint(8, 80)
            for _ in range(num_user_requests):
                task = Task.generate(task_id, user, satellites)
                tasks.append(task)
                all_observation_opportunities.extend(task.observation_opportunities)
                task_id += 1

        return Instance(satellites, users, tasks, all_observation_opportunities)
    
    def filter_by_user(self, user_id):
        # Filtrer les tâches (requêtes) pour un utilisateur spécifique
        filtered_tasks = [task for task in self.tasks if task.user.id == user_id]

        # Filtrer les opportunités d'observation associées à ces tâches
        filtered_obs = [obs for obs in self.observation_opportunities if obs.user_o.id == user_id]

        # Créer une nouvelle instance avec ces tâches et opportunités d'observation filtrées
        return Instance(self.satellites, self.users, filtered_tasks, filtered_obs)

    
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
                formatted_output += f"      Satellite: {opp.satellite_o}, Start: {opp.t_start_o}, End: {opp.t_end_o}, Duration: {opp.duration_o}, Reward: {opp.reward_o}\n"

        return formatted_output

""" # Paramètres de l'expérimentation
num_satellites = 5
num_exclusive_users = 4
num_tasks_per_user = 20  # Nombre de requêtes par utilisateur exclusif
instance = Instance.generate(num_satellites, num_exclusive_users, num_tasks_per_user)   
test = {}
for user in instance.users:
    test[user.id] = []
for task in instance.tasks:
    test[task.user.id].append(task.id)
for key in test:
    print(str(key) + " : " + str(test[key]))
    print("\n") """