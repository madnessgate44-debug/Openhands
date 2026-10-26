---
name: performance-engineering
description: "Diagnose and fix performance problems. Use when something is slow, the bundle is too big, or Core Web Vitals regress."
triggers:
- performance
- profiling
- core web vitals
- bundle size
- latency
- memory
---

# Performance Engineering

- Measure before optimizing; capture a baseline and a profile.
- Optimize the actual bottleneck, not the one that looks suspicious.
- For the web: watch LCP, INP, CLS, and bundle size; lazy-load and split.
- For the backend: watch query plans, N+1 access, and payload size.
- Re-measure after the change and report both numbers.
