import json, random
def weighted_sample(items,weights,k,seed=0):
    if len(items)!=len(weights) or k<0 or k>len(items): raise ValueError("invalid sample size")
    if any(w<0 for w in weights): raise ValueError("negative weight")
    pool=list(zip(items,weights)); out=[]; rng=random.Random(seed)
    for _ in range(k):
        total=sum(w for _,w in pool)
        if total<=0: raise ValueError("no positive weight")
        needle=rng.random()*total; acc=0
        for i,(item,w) in enumerate(pool):
            acc+=w
            if needle<acc: out.append(item); pool.pop(i); break
    return out
def serialize_metrics(metrics): return json.dumps(metrics,sort_keys=True,separators=(",",":"),ensure_ascii=False)
