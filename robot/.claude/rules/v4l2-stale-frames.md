# V4L2 Stale Frame Buffer Issue

## The Problem

When using V4L2 cameras with a kernel ring buffer (e.g. `buffersize=4`), frames go stale whenever `cam.read()` stops being called — for instance during a blocking `robot.rotate()` call.

**What happens:**

1. V4L2 fills all buffer slots within ~44 ms (at 90 fps, 4 buffers ≈ 44 ms).
2. Once every slot holds an unread frame, the kernel **stops capturing** — there are no free buffers to write into.
3. When `cam.read()` resumes seconds later, the first N frames returned are the ones captured *before* the pause, not after it.

## Symptoms

- After a turn, the first 3–4 ArUco/line-detection readings still show the **previous** heading.
- A PD controller that initialises on the first frame gets a ~90° error, producing a violent overcorrection (e.g. `lv=1.82, rv=−1.78`).
- The stale angle exactly matches the *correct* angle of the previous segment — the smoking gun.

## The Fix — Flush After Any Blocking Pause

After any operation that blocks camera reads (turns, long sleeps, motor sequences), drain the stale buffers before using frames for control:

```python
# flush stale V4L2 frames captured before/during the blocking call
for _ in range(cam.buffersize + 1):   # buffersize + 1 to be safe
    cam.read()
```

Use `buffersize + 1` (typically 5 frames) to guarantee every pre-pause frame is discarded.

## Where This Pattern Is Already Used

- `circle_line/sockets.py` — `FLUSH_FRAMES = 5` after motor re-enable.
- `app.py` — flush added after `robot.rotate()` returns, before `_drive_move()` starts.

## Rule of Thumb

> **Any time there is a gap of more than ~50 ms without a `cam.read()`, flush `buffersize + 1` frames before trusting camera data.**
