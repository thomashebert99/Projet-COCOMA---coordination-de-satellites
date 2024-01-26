import random
import pprint

def generate_satellite(i):
    t_start_s = random.uniform(0, 100)
    t_end_s = t_start_s + random.uniform(0, 300 - t_start_s)
    capacity = random.randint(1, 10)
    transition_time = 1

    satellite = {
        "id": f"satellite_{i+1}",
        "t_start_s": t_start_s,
        "t_end_s": t_end_s,
        "capacity": capacity,
        "transition_time": transition_time
    }
    
    return satellite

def generate_all_users(num_exclusive_users, satellites, total_time=300):
    exclusive_windows_all_users = []
    users = []

    # S'assurer qu'il y a suffisamment de satellites pour les utilisateurs exclusifs
    if num_exclusive_users > len(satellites):
        raise ValueError("Il n'y a pas assez de satellites pour le nombre d'utilisateurs exclusifs")

    exclusive_satellites = random.sample(satellites, num_exclusive_users)

    # Générer des utilisateurs exclusifs avec des fenêtres non-chevauchantes et associer chaque utilisateur à un satellite
    for i, satellite in enumerate(exclusive_satellites, start=1):
        exclusive_windows = generate_exclusive_windows(8, (15, 20), total_time, exclusive_windows_all_users)
        exclusive_windows_all_users.extend(exclusive_windows)
        windows_for_user = [(satellite["id"], start, end) for start, end in exclusive_windows]  # Format des fenêtres exclusives
        users.append({
            "id": f"exclusive_user_{i}",
            "satellite": satellite["id"],
            "exclusive_windows": windows_for_user,
            "priority": random.randint(10, 50)
        })

    users.append({
        "id": "central_planner",  # Identifiant pour le planificateur central
        "exclusive_windows": [],
        "priority": random.randint(1, 5)
    })

    return users


def generate_exclusive_windows(num_windows, window_length_range, total_time, existing_windows):
    windows = []
    while len(windows) < num_windows:
        start = random.uniform(0, total_time - window_length_range[1])
        end = start + random.uniform(*window_length_range)
        if not any(existing_start <= start < existing_end or existing_start < end <= existing_end for existing_start, existing_end in existing_windows + windows):
            windows.append((start, end))
    return windows


def generate_observation_opportunity(request, satellite, time_window_length):
    # Fenêtre temporelle pour l'opportunité d'observation
    t_start_o = random.uniform(request["t_start_r"], request["t_end_r"] - time_window_length)
    t_end_o = t_start_o + time_window_length

    observation = {
        "t_start_o": t_start_o,
        "t_end_o": t_end_o,
        "duration": 5,  # Durée fixée à 5 minutes
        "reward": request["reward"],  # Récompense héritée de la requête
        "satellite": satellite,  # Satellite assigné
        "user": request["user"],  # Utilisateur hérité de la requête
        "priority": request["user"]["priority"]  # Priorité héritée de l'utilisateur
    }

    return observation

def generate_request(user, satellites, task_id, request_time_window=(0, 300)):
    t_start_r = random.uniform(*request_time_window)
    t_end_r = t_start_r + random.uniform(10, 20)
    duration = 5
    reward = random.randint(10, 50) if user["priority"] >= 10 else random.randint(1, 5)
    gps_position = (random.uniform(-90, 90), random.uniform(-180, 180))

    satellite_for_observation = user["satellite"] if "satellite" in user and user["satellite"] else random.choice(satellites)

    observation_opportunities = [generate_observation_opportunity(
        {
            "t_start_r": t_start_r,
            "t_end_r": t_end_r,
            "duration": duration,
            "reward": reward,
            "gps_position": gps_position,
            "user": user
        }, satellite_for_observation, duration) for _ in range(10)]

    request = {
        "id": f"task_{task_id}",  # Ajout d'un identifiant unique
        "t_start_r": t_start_r,
        "t_end_r": t_end_r,
        "duration": duration,
        "reward": reward,
        "gps_position": gps_position,
        "user": user,
        "observation_opportunities": observation_opportunities
    }

    return request




def generate_EOSCSP_instance(num_satellites, num_exclusive_users, num_tasks_per_user):
    satellites = [generate_satellite(i) for i in range(num_satellites)]
    users = generate_all_users(num_exclusive_users, satellites)

    requests = []
    task_id = 1
    for user in users:
        num_user_requests = num_tasks_per_user if user["exclusive_windows"] else random.randint(8, 80)
        for _ in range(num_user_requests):
            request = generate_request(user, satellites, task_id)
            requests.append(request)
            task_id += 1

    instance = {
        "Satellites": satellites,
        "Users": users,
        "Requests": requests
    }

    return instance


def format_eoscsp_instance(instance):
    formatted_output = "EOSCSP Instance:\n\n"

    formatted_output += "Satellites:\n"
    for sat in instance["Satellites"]:
        formatted_output += f"  ID: {sat['id']}, Start: {sat['t_start_s']}, End: {sat['t_end_s']}, Capacity: {sat['capacity']}, Transition Time: {sat['transition_time']}\n"
    
    formatted_output += "\nUsers:\n"
    for user in instance["Users"]:
        formatted_output += f"  ID: {user['id']}, Priority: {user['priority']}, Exclusive Windows: "
        if user.get("exclusive_windows"):
            for window in user["exclusive_windows"]:
                formatted_output += f"[Satellite {window[0]}, Start: {window[1]}, End: {window[2]}] "
        else:
            formatted_output += "None"
        formatted_output += "\n"
    
    formatted_output += "\nTasks:\n"
    for task in instance["Requests"]:
        formatted_output += f"  ID: {task['id']}, Start: {task['t_start_r']}, End: {task['t_end_r']}, Duration: {task['duration']}, Reward: {task['reward']}, Position: {task['gps_position']}, Requester: {task['user']['id']}\n"
        formatted_output += "    Observation Opportunities:\n"
        for opp in task["observation_opportunities"]:
            formatted_output += f"      Satellite: {opp['satellite']}, Start: {opp['t_start_o']}, End: {opp['t_end_o']}, Duration: {opp['duration']}, Reward: {opp['reward']}\n"

    return formatted_output


# Exemple d'utilisation avec les valeurs de l'article
example_instance = generate_EOSCSP_instance(5, 4, 20)  # 5 satellites, 4 utilisateurs exclusifs, 20 requêtes par utilisateur exclusif
# Utiliser pprint pour un affichage formaté
print(format_eoscsp_instance(example_instance))
