from copy import deepcopy


def execute(obj: dict) -> None:
    for job in obj.get("jobs", {}).values():
        build_job(obj, job)


def build_job(obj: dict, job: dict) -> None:
    # get the first step that references a command
    index = next(
        (
            i
            for i, step in enumerate(job.get("steps", []))
            if step_is_calling_a_command(step)
        ),
        None,
    )

    if index is None:
        return  # No more steps have a command

    # we need to clear the old step from the steps, as it's invalid
    # in github world.
    step = job["steps"].pop(index)

    step_env = step.get("env", {})
    job_env = job.get("env", {})
    global_env = obj.get("env", {})

    command_name = step["command"]
    command = get_command(obj, command_name)
    populate_env_on_command(
        command, step_env=step_env, global_env={**global_env, **job_env}
    )
    command_steps = command.get("steps", [])

    # We go in reverse, as we're inserting at the same index each time.
    # This will result in the steps being added in order.

    for command_step in reversed(command_steps):
        job["steps"].insert(index, command_step)

    # Move on to the next step.
    # We do this recursively, reading from the start of the steps each time,
    # as a command can reference another command.

    build_job(obj, job)


def step_is_calling_a_command(step: dict) -> bool:
    return "command" in step


def get_command(obj: dict, name: str) -> dict:
    command = obj["commands"][name]
    return deepcopy(command)


def populate_env_on_command(command: dict, step_env: dict, global_env: dict) -> None:
    for step in command.get("steps", []):
        step.setdefault("env", {})

        # the command environment is a default fallback. If a step defines
        # a value already, ignore it
        for key, val in command.get("env", {}).items():
            step["env"].setdefault(key, val)

        # global env contains the job env too, since it doesn't matter at this level.
        # We should pop the keys if they exist, since they always overwrite the command
        # scope.
        for key in global_env:
            step["env"].pop(key, None)

        # Set the environment from the parent command call, which always overwrites.
        step["env"].update(step_env)

        # cleanup!
        if not step["env"]:
            step.pop("env")
