import subprocess
import json
import generator

def sort_observations(observations):
    return sorted(observations, key=lambda o: (o.user_o.priority, o.t_start_o))


def greedy_eoscsp_solver(instance, R):
    # Initialiser l'allocation vide
    M = {}
    # Trier les opportunités d'observation
    O_sorted = sort_observations(instance.observation_opportunities)    

    for o in O_sorted:
        t = first_slot(o, instance, R)
        if t != None:
            M[o] = t
            # Mettre à jour les opportunités d'observation restantes
            O_sorted = [op for op in O_sorted if op.request_o != o.request_o]

    return M

def first_slot(o, instance, R):
    satellite = o.satellite_o
    if len(R[satellite.id]) < satellite.capacity:
        if not R[satellite.id]:
            if o.t_end_o >= o.t_start_o + o.duration_o:
                R[satellite.id].append((o, (satellite.id, o.t_start_o)))
                return (satellite.id, o.t_start_o)
        else:
            i = 0
            while i <= len(R[satellite.id]):
                t_start_prime = o.t_start_o
                if i > 0:
                    observation_prev, (_, t_prev) = R[satellite.id][i - 1]
                    t_start_prime = max(o.t_start_o, t_prev + observation_prev.duration_o + satellite.transition_time)
                if t_start_prime + o.duration_o <= o.t_end_o:
                    if i == len(R[satellite.id]):
                        t_upper = o.t_end_o
                        t_end_prime = t_start_prime + o.duration_o
                    else:
                        obs, (_, t_i) = R[satellite.id][i]
                        t_upper = t_i
                        t_end_prime = t_start_prime + o.duration_o + satellite.transition_time
                    if t_start_prime < t_end_prime <= t_upper:
                        R[satellite.id].insert(i, (o, (satellite.id, t_start_prime)))
                        return (satellite.id, t_start_prime)
                i+=1

    return None

def sort_requests(requests):
    """
    Trie les requêtes en fonction de la priorité de l'utilisateur et du temps de début de la requête.
    
    Args:
        requests (list): Liste des requêtes (tasks) à trier.

    Returns:
        list: Liste des requêtes triées.
    """
    return sorted(requests, key=lambda r: (r.user.priority, r.t_start_r))


def s_dcop_eoscsp_solver(instance):
    R = {satellite.id: [] for satellite in instance.satellites}
    # Étape 1 : Résoudre pour le planificateur central (u0)
    central_planner_assignments = greedy_eoscsp_solver(instance.filter_by_user("central_planner"), R)

    # Étape 2 : Résoudre pour chaque utilisateur exclusif
    exclusive_assignments = {}
    for user in instance.users:
        if user.exclusive_windows:  # Utilisateurs avec fenêtres exclusives
            exclusive_assignments[user.id] = greedy_eoscsp_solver(instance.filter_by_user(user.id), R)

    # Étape 3 : Identifier les requêtes non assignées
    assigned_requests = set([o.request_o for o in central_planner_assignments])
    unassigned_requests = [r for r in instance.tasks if r not in assigned_requests]
    Rsorted = sort_requests(unassigned_requests)

    # Étape 4-6 : Construire et résoudre le DCOP pour chaque requête triée
    for r in Rsorted:
        dcop_problem = build_DCOP_yaml(r.observation_opportunities, central_planner_assignments, exclusive_assignments, instance)
        dcop_solutions = solve_DCOP(dcop_problem)

        # Intégrer directement les solutions DCOP dans les affectations
        for user_id, assignments in dcop_solutions.items():
            exclusive_assignments[user_id] = assignments

    # Étape 7-9 : Rassembler les solutions pour le planificateur central et retourner la solution complète
    non_exclusive_assignments = {o: time for user_id, user_assignments in exclusive_assignments.items() for o, time in user_assignments.items() if o.user_o.id != user_id}
    total_assignments = {**central_planner_assignments, **non_exclusive_assignments}
    return total_assignments

""" def build_DCOP(observations, central_planner_assignments, exclusive_assignments, instance):
    agents = {user.id for user in instance.users if user.exclusive_windows and any(
        observation.satellite_o in [window[0] for window in user.exclusive_windows] 
        and any(
            observation.t_start_o < end and observation.t_end_o > start 
            for _, start, end in user.exclusive_windows
        )
        for observation in observations
    )}

    # Création des variables et domaines pour chaque agent
    variables = {}
    domains = {}
    for observation in observations:
        for user_id in agents:
            var_name = f"x_{user_id}_{observation.id}"
            variables[var_name] = Variable(var_name, Domain(['0', '1']))
            domains[var_name] = Domain(['0', '1'])

    # Contraintes
    constraints = []

    # Contrainte 1 : Une observation par requête
    for observation in observations:
        involved_vars = [f"x_{user_id}_{observation.id}" for user_id in agents]
        constraint_str = f"sum([{','.join(involved_vars)}]) <= 1"
        constraints.append(constraint_from_str(f"one_observation_per_request_{observation.id}", involved_vars, constraint_str, domains))

    # Contrainte 2 : Les satellites ne sont pas surchargés
    for satellite in instance.satellites:
        involved_vars = [
            f"x_{user_id}_{observation.id}"
            for user_id in agents
            for observation in observations
            if observation.satellite_o == satellite.id
        ]
        current_capacity = satellite.capacity - sum(
            1 for o, _ in central_planner_assignments.items() if o.satellite_o == satellite.id
        ) - sum(
            1 for o, _ in exclusive_assignments.get(user_id, {}).items() if o.satellite_o == satellite.id for user_id in agents
        )
        constraint_str = f"sum([{','.join(involved_vars)}]) <= {current_capacity}"
        constraints.append(constraint_from_str(f"satellite_capacity_{satellite.id}", involved_vars, constraint_str, domains))

    # Contrainte 3 : Un agent par observation
    for observation in observations:
        involved_vars = [f"x_{user_id}_{observation.id}" for user_id in agents]
        constraint_str = f"sum([{','.join(involved_vars)}]) <= 1"
        constraints.append(constraint_from_str(f"one_agent_per_observation_{observation.id}", involved_vars, constraint_str, domains))

    # Construction du problème DCOP
    dcop_yaml = {
        'name': 'EOSCSP',
        'description': 'DCOP for EOSCSP problem',
        'variables': {v.name: {'domain': v.domain.name} for v in variables.values()},
        'domains': {d.name: list(d.values) for d in domains.values()},
        'agents': list(agents),
        'constraints': [str(c) for c in constraints]
    }

    dcop = load_dcop_from_dict(dcop_yaml)
    return dcop """

def build_DCOP_yaml(observations, central_planner_assignments, exclusive_assignments, instance):
    yaml_content = "name: EOSCSP\n"
    yaml_content += "objective: min\n\n"

    # Définir les domaines
    yaml_content += "domains:\n  binary:\n    values: [0, 1]\n\n"

    # Identifier les agents et créer les variables
    yaml_content += "variables:\n"
    agents = set()
    for user in instance.users:
        if user.exclusive_windows:
            print(user.id)
            for obs in observations:
                for window in user.exclusive_windows:
                    print(obs.satellite_o.id, window[0])
                    print(obs.t_start_o, obs.t_end_o)
                    print(window[1], window[2])

                if any(obs.satellite_o.id == window[0] and (window[1] < obs.t_end_o and window[2] > obs.t_start_o) 
                       for window in user.exclusive_windows):
                    agents.add(user.id)
                    var_name = f"x_{user.id}_{obs.id}"
                    yaml_content += f"  {var_name}:\n    domain: binary\n\n"
    print(agents)

    # Définir les contraintes
    yaml_content += "constraints:\n"
    
    # Contrainte 1: Une observation par requête pour tous les agents
    for obs in observations:
        constraint_name = f"one_observation_{obs.id}"
        yaml_content += f"  {constraint_name}:\n"
        yaml_content += "    type: intention\n"
        involved_vars = [f"x_{agent_id}_{obs.id}" for agent_id in agents]
        yaml_content += f"    function: 'sum([{','.join(involved_vars)}]) <= 1'\n\n"

    # Contrainte 2: Capacité des satellites
    for satellite in instance.satellites:
        constraint_name = f"satellite_capacity_{satellite.id}"
        yaml_content += f"  {constraint_name}:\n"
        yaml_content += "    type: intention\n"
        
        involved_vars = []
        for agent_id in agents:
            for obs in observations:
                if obs.satellite_o.id == satellite.id:
                    var_name = f"x_{agent_id}_{obs.id}"
                    involved_vars.append(var_name)

        # Calcul de la capacité actuelle du satellite
        assigned_observations = set()
        for obs, _ in central_planner_assignments.items():
            if obs.satellite_o.id == satellite.id:
                assigned_observations.add(obs.id)
        for user_assignments in exclusive_assignments.values():
            for obs, _ in user_assignments.items():
                if obs.satellite_o.id == satellite.id:
                    assigned_observations.add(obs.id)
        
        print(len(assigned_observations))

        current_capacity = satellite.capacity - len(assigned_observations)
        yaml_content += f"    function: 'sum([{','.join(involved_vars)}]) <= {current_capacity}'\n\n"


    # Contrainte 3: Un agent par observation
    for obs in observations:
        constraint_name = f"one_agent_per_observation_{obs.id}"
        yaml_content += f"  {constraint_name}:\n"
        yaml_content += "    type: intention\n"
        involved_vars = [f"x_{agent_id}_{obs.id}" for agent_id in agents]
        yaml_content += f"    function: 'sum([{','.join(involved_vars)}]) <= 1'\n\n"

    # Liste des agents
    yaml_content += "agents:\n"
    for agent_id in agents:
        yaml_content += f"  - {agent_id}\n"

    # Écrire le contenu dans un fichier
    with open("dcop_eoscsp.yaml", "w") as file:
        file.write(yaml_content)

    return "dcop_eoscsp.yaml"


""" def solve_DCOP(dcop_problem, algorithm='dpop'):
    if algorithm not in pydcop.algorithms.available_algorithms():
        raise ValueError(f"Algorithme {algorithm} non disponible")

    # Construction de l'algorithme avec le problème DCOP
    algo = build_algorithm(dcop_problem, algo=algorithm)
    computation_graph = ComputationGraph(dcop_problem)
    result = algo.solve(computation_graph)

    # Formatter les résultats pour correspondre au format d'`exclusive_assignment`
    formatted_result = {}
    for var_name, value in result.items():
        user_id, observation_id = var_name.split('_')[1:]
        if value == "1":
            if user_id not in formatted_result:
                formatted_result[user_id] = {}
            # Trouver l'observation correspondante dans le problème DCOP
            observation = next(obs for obs in dcop_problem.observations if obs.id == observation_id)
            formatted_result[user_id][observation_id] = observation.satellite_o

    return formatted_result """

def solve_DCOP(dcop_yaml_file, algorithm='dpop'):
    output_file = "results.json"
    command = f"pydcop --output {output_file} solve --algo {algorithm} {dcop_yaml_file}"
    
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Une erreur s'est produite lors de l'exécution de pydcop: {e}")

    try:
        with open(output_file, 'r') as f:
            results = json.load(f)
            assignments = results.get("assignment", {})
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier de résultats '{output_file}' n'a pas été trouvé.")

    # Formatter les résultats pour correspondre au format attendu
    formatted_result = {}
    for var_name, value in assignments.items():
        user_id, observation_id = var_name.split('_')[1:]
        if value == "1":
            if user_id not in formatted_result:
                formatted_result[user_id] = {}
            formatted_result[user_id][observation_id] = True  # Ou une autre valeur appropriée

    return formatted_result



# Paramètres de l'expérimentation
num_satellites = 5
num_exclusive_users = 4
num_tasks_per_user = 20  # Nombre de requêtes par utilisateur exclusif

# Générer l'instance EOSCSP
instance = generator.Instance.generate(num_satellites, num_exclusive_users, num_tasks_per_user)

# Appliquer l'algorithme s_dcop EOSCSP solver
solution = s_dcop_eoscsp_solver(instance)

# Afficher ou analyser la solution
print(solution)