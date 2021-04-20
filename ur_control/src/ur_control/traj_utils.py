import numpy as np
from ur_control import transformations


def spiral(radius, theta_offset, revolutions, steps):
    theta = np.linspace(0, 2*np.pi*revolutions, steps) + theta_offset
    x = radius*np.cos(theta)
    y = radius*np.sin(theta)
    return x, y


def get_conical_helix_trajectory(p1, p2, steps, revolutions=5.0):
    """ Compute Cartesian conical helix between 2 points"""
    euclidean_dist = np.linalg.norm(np.array(p2[:2])-np.array(p1[:2]))
    radius = np.linspace(euclidean_dist, 0, steps)
    theta_offset = np.arctan2((p1[1] - p2[1]), (p1[0]-p2[0]))

    x, y = spiral(radius, theta_offset, revolutions, steps)
    x += p2[0]
    y += p2[1]
    z = np.linspace(p1[2]-(p1[2]-p2[2])/2, p2[2], steps)
    return concat_vec(x, y, z, steps)


def get_spiral_trajectory(p1, p2, steps, revolutions=5.0, from_center=False, inverse=False):
    """ Compute Cartesian conical helix between 2 points"""
    euclidean_dist = np.linalg.norm(np.array(p2[:2])-np.array(p1[:2]))
    if from_center:  # start the spiral as if p1 is the center and p2 is the farthest point
        radius = np.linspace(0, euclidean_dist, steps)
        theta_offset = 0.0
    else:
        # Compute the distance from p1 to p2 and start the spiral as if p2 is the center
        radius = np.linspace(euclidean_dist, 0, steps)
        # Hack for some reason this offset does not work for changes w.r.t Z
        if inverse:
            theta_offset = np.arctan2((p2[1] - p1[1]), (p2[0]-p1[0]))
        else:
            theta_offset = np.arctan2((p1[1] - p2[1]), (p1[0]-p2[0]))
    x, y = spiral(radius, theta_offset, revolutions, steps)
    sign = 1. if not inverse else -1.  # super hack, there is something fundamentally wrong with Z
    x += p2[0] * sign
    y += p2[1] * sign
    z = np.linspace(p1[2]-(p1[2]-p2[2])/2, p2[2], steps)
    return concat_vec(x, y, z, steps)


def get_circular_trajectory(p1, p2, steps, revolutions=1.0, from_center=False, inverse=False):
    euclidean_dist = np.linalg.norm(np.array(p2[:2])-np.array(p1[:2]))
    if from_center:  # start the spiral as if p1 is the center and p2 is the farthest point
        theta_offset = 0.0
    else:
        # Compute the distance from p1 to p2 and start the spiral as if p2 is the center
        # Hack for some reason this offset does not work for changes w.r.t Z
        if inverse:
            theta_offset = np.arctan2((p2[1] - p1[1]), (p2[0]-p1[0]))
        else:
            theta_offset = np.arctan2((p1[1] - p2[1]), (p1[0]-p2[0]))
    x, y = spiral(euclidean_dist, theta_offset, revolutions, steps)
    x += p2[0]
    y += p2[1]
    z = np.zeros(steps)+p1[2]
    return concat_vec(x, y, z, steps)


def concat_vec(x, y, z, steps):
    x = x.reshape(-1, steps)
    y = y.reshape(-1, steps)
    z = z.reshape(-1, steps)
    return np.concatenate((x, y, z), axis=0).T


def get_plane_direction(plane, radius):
    VALID_DIRECTIONS = ('+X', '+Y', '+Z', '-X', '-Y', '-Z')
    DIRECTION_INDEX = {'X': 0, 'Y': 1, 'Z': 2}

    assert plane in VALID_DIRECTIONS, "Invalid direction: %s" % plane

    direction_array = [0., 0., 0., 0., 0., 0.]
    sign = 1. if '+' in plane else -1.
    direction_array[DIRECTION_INDEX.get(plane[1])] = radius * sign

    return np.array(direction_array)


def compute_trajectory(initial_pose, plane, radius, radius_direction, steps=100, revolutions=5, from_center=True,  trajectory_type="circular"):
    """
        Compute a trajectory "circular" or "spiral":
        plane: string, only 3 valid options "XY", "XZ", "YZ", is the plane w.r.t to the robot base where the trajectory will be drawn
        radius: float, size of the trajectory
        radius_direction: string, '+X', '+Y', '+Z', '-X', '-Y', '-Z' direction to compute the radius, valid directions depend on the plane selected
        steps: int, number of steps for the trajectory
        revolutions: int, number of times that the circle is drawn or the spiral's revolutions before reaching its end.
        from_center: bool, whether to start the trajectory assuming the current position as center (True) or the radius+radius_direction as center (False)
                            [True] is better for spiral trajectory while [False] is better for the circular trajectory, though other options are okay.
        trajectory_type: string, "circular" or "spiral"
    """

    direction = get_plane_direction(radius_direction, radius)

    if plane == "XZ":
        assert "Y" not in radius_direction, "Invalid radius direction %s for plane %s" % (radius_direction, plane)
        to_plane = [np.pi/2, 0, 0]
    elif plane == "YZ":
        assert "X" not in radius_direction, "Invalid radius direction %s for plane %s" % (radius_direction, plane)
        to_plane = [0, np.pi/2, 0]
    elif plane == "XY":
        assert "Z" not in radius_direction, "Invalid radius direction %s for plane %s" % (radius_direction, plane)
        to_plane = [0, 0, 0]
    else:
        raise ValueError("Invalid value for plane: %s" % plane)

    target_pose = transformations.pose_euler_to_quaternion(initial_pose, direction, ee_rotation=False)

    # print("Initial", np.round(spalg.translation_rotation_error(target_pose, arm.end_effector()), 4))
    target_orientation = transformations.vector_to_pyquaternion(transformations.quaternion_from_euler(*to_plane))

    initial_pose = initial_pose[:3]
    final_pose = target_pose[:3]

    if from_center:
        p1 = np.zeros(3)
        p2 = target_orientation.rotate(initial_pose - final_pose)
    else:
        p1 = target_orientation.rotate(initial_pose - final_pose)
        p2 = np.zeros(3)

    if trajectory_type == "circular":
        # Hack for some reason this offset does not work for changes w.r.t Z
        traj = get_circular_trajectory(p1, p2, steps, revolutions, from_center=from_center, inverse=("Z" in radius_direction))
    if trajectory_type == "spiral":
        # Hack for some reason this offset does not work for changes w.r.t Z
        traj = get_spiral_trajectory(p1, p2, steps, revolutions, from_center=from_center, inverse=("Z" in radius_direction))

    traj = np.apply_along_axis(target_orientation.rotate, 1, traj)
    trajectory = traj + final_pose
    trajectory = [np.concatenate([t, target_pose[3:]]) for t in trajectory]

    return trajectory
