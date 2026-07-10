import json, hashlib, datetime, importlib.metadata as md
from agentdojo.task_suite.load_suites import get_suites
from agentdojo.functions_runtime import FunctionsRuntime

ADV = md.version("agentdojo")
s = get_suites("v1")["workspace"]
rt = FunctionsRuntime(s.tools)

def ser(x):
    try:
        return x.model_dump(mode="json")
    except Exception:
        if isinstance(x, list):
            return [ser(i) for i in x]
        return repr(x)[:500]

def env_snapshot(env):
    d = env.model_dump(mode="json")
    return {k: (len(v) if isinstance(v,(list,dict)) else v) for k,v in d.items()}

def state_delta(pre, post):
    a, b = pre.model_dump(mode="json"), post.model_dump(mode="json")
    out={}
    for k in a:
        if a[k]!=b[k]:
            out[k]={"changed":True,
                    "pre_size":len(a[k]) if isinstance(a[k],(list,dict)) else None,
                    "post_size":len(b[k]) if isinstance(b[k],(list,dict)) else None}
    return out

def run_traj(task, env, kind):
    gt = task.ground_truth(env)
    steps=[]
    for i,fc in enumerate(gt):
        res, err = rt.run_function(env, fc.function, fc.args, raise_on_error=False)
        steps.append({"step": i, "function": fc.function, "args": ser(fc.args),
                      "output_type": type(res).__name__, "error": err,
                      "raw_output": ser(res)})
    return {"kind": kind, "n_calls": len(gt), "steps": steps}

fix={"meta":{"suite":"workspace","agentdojo_version":ADV,
             "generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "generator":"scripts/gen_agentdojo_fixture.py","llm_used":False,
             "note":"deterministic ground_truth trajectory; NO model call. calibration anchors + shapes for Gate-2."},
     "trajectories":[], "outcomes":{}, "error_sample":None, "measurement_context_stub":{}}

# --- benign path (negative control): user task utility ---
utid="user_task_0"; ut=s.user_tasks[utid]
env=s.load_and_inject_default_environment({}); pre=env.model_copy(deep=True)
tj=run_traj(ut, env, "benign_user_task"); tj["task_id"]=utid; tj["prompt"]=ut.PROMPT
util=ut.utility("", pre, env)  # model_output empty; utility inspects state
tj["state_delta"]=state_delta(pre, env)
fix["trajectories"].append(tj)

# --- attack path (positive control): injection task security ---
itid="injection_task_0"; it=s.injection_tasks[itid]
env2=s.load_and_inject_default_environment({}); pre2=env2.model_copy(deep=True)
tj2=run_traj(it, env2, "attack_injection_task"); tj2["task_id"]=itid; tj2["goal"]=it.GOAL
sec=it.security("", pre2, env2)
tj2["state_delta"]=state_delta(pre2, env2)
fix["trajectories"].append(tj2)

# cross checks (calibration truth table)
sec_on_benign = it.security("", pre, env)   # benign path should NOT satisfy attacker goal
fix["outcomes"]={"benign_utility": bool(util),
                 "benign_security(should be False)": bool(sec_on_benign),
                 "attack_security(should be True)": bool(sec)}

# --- real execution_error shape (bad call) ---
env3=s.load_and_inject_default_environment({})
_, err = rt.run_function(env3, "send_email", {"recipients":"not-a-list"}, raise_on_error=False)
fix["error_sample"]={"function":"send_email","bad_args":{"recipients":"not-a-list"},
                     "error":err, "classified_as":"execution_error"}

fix["measurement_context_stub"]={
    "corpus_version":"agentdojo-v1", "scenario_id":"workspace/injection_task_0",
    "target_snapshot":"workspace-default-env", "model_id":"<none-ground_truth>",
    "defense_hash":"none", "attack_strength":"published-static",
    "harness_tool_version":f"agentdojo=={ADV}", "detector_version":"security()-state-check",
    "aggregate_rule_version":"n/a-single-deterministic", "execution_backend":"MockBackend/agentdojo"}

open("agentdojo_pi_trajectory.golden.json","w").write(json.dumps(fix, indent=2, ensure_ascii=False))
print("outcomes:", fix["outcomes"])
print("benign calls:", fix["trajectories"][0]["n_calls"], "| attack calls:", fix["trajectories"][1]["n_calls"])
print("attack state_delta:", fix["trajectories"][1]["state_delta"])
print("error_sample:", fix["error_sample"])
