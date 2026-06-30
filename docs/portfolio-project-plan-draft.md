# Portfolio Project Plan Draft: ML/DL x Network Security

> Status: draft
>
> Purpose: turn the discussion after `01-honest-nids` into a concrete portfolio roadmap. The goal is not to build more benchmark classifiers, but to show credible ability across IP networking, network security, detection engineering, ML/DL, and operational risk.

---

## 1. Starting Point

`01-honest-nids` is valuable because it does the opposite of a typical "99% accuracy NIDS" portfolio project. It focuses on leakage, temporal split, cross-dataset generalisation, base-rate thinking, and honest evaluation.

Its main limitation is also clear: public NetFlow benchmark datasets make the project look closer to a research-reproduction and evaluation-methodology exercise than a deployable security engineering system. That is not a flaw in the current project; it is a boundary imposed by the data and task design.

The next portfolio projects should therefore add the missing dimensions:

- Telemetry-first thinking: Zeek, Suricata, DNS, TLS, BGP, VPC Flow Logs, auth logs.
- Detection engineering: ATT&CK mapping, rules, hypotheses, runbooks, analyst workflow.
- Operational constraints: alert budget, base rate, false-positive cost, drift, retraining.
- ML/DL pragmatism: use ML where it improves triage or detection, not as decoration.
- Network expertise: protocol semantics, routing, flow/session behaviour, asset context.
- Governance: model cards, data cards, privacy limits, monitoring and auditability.

The portfolio should show that I can move from "train a classifier" to "design a detection capability."

---

## 2. Project Selection Principles

Use these principles when selecting projects after `01-honest-nids`.

| Principle | Meaning |
|---|---|
| Security realism | The project should resemble a SOC, network security, cloud security, or detection engineering workflow. |
| Network depth | It should require actual understanding of protocols, logs, routing, flows, or telemetry sources. |
| ML/DL fit | The model should solve a real problem such as prioritisation, anomaly detection, representation learning, sequence modelling, or drift monitoring. |
| Data availability | Public data must be obtainable and legally usable; when data is imperfect, the limitation must be explicit. |
| Portfolio contrast | Each project should show a different capability from `01-honest-nids`. |
| Deployability | The output should include a detector, runbook, dashboard, API, reproducible pipeline, or monitoring story. |

---

## 3. Candidate Projects

### Project A: Zeek + ATT&CK Detection Engineering Lab

**Short description**

Build a telemetry-first detection lab from PCAP/network traffic to Zeek logs, rule-based detections, ML anomaly scoring, ATT&CK mapping, alert budget analysis, and analyst-facing investigation notes.

**Why this complements project 1**

`01-honest-nids` studies whether benchmark NIDS models generalise. This project starts from the opposite direction: real network telemetry and concrete detection hypotheses. It would show security engineering maturity beyond ML evaluation.

**Possible data sources**

- Malware-Traffic-Analysis.net PCAPs.
- Stratosphere CTU / CTU-13 botnet traffic.
- IoT-23 malicious IoT traffic.
- Public Zeek/Suricata training datasets where licenses permit.

**Technical components**

- PCAP to Zeek logs: `conn.log`, `dns.log`, `http.log`, `ssl.log`, `x509.log`, `files.log`.
- Optional Suricata alerts for rule-based signal.
- Feature engineering from connection, DNS, TLS, HTTP and host aggregation.
- Baseline rules mapped to MITRE ATT&CK techniques.
- ML anomaly scoring: Isolation Forest, Local Outlier Factor, autoencoder, or LightGBM where labels exist.
- Alert budget: how many alerts per day per threshold, analyst queue size, precision/recall tradeoff.
- Drift and deployment notes.

**Expected deliverables**

- Reproducible pipeline: PCAP -> logs -> features -> detections -> report.
- Detection cards: hypothesis, data source, ATT&CK technique, logic, expected false positives, triage steps.
- Notebook/report comparing rule-only, ML-only, and hybrid detection.
- Small dashboard or static HTML report for alert review.

**Portfolio value**

Very high. This is closest to real detection engineering and SOC analytics. It directly addresses the "research reproduction" weakness of project 1.

---

### Project B: DNS Tunneling and DGA Detection

**Short description**

Build a DNS security analytics project that detects suspicious domains and host behaviour using lexical features, sequence models, aggregation, and operational thresholds.

**Why this complements project 1**

It moves from NetFlow-level classification to protocol-aware detection. DNS is a practical security data source, commonly available in enterprise networks, and strongly connected to malware, C2, phishing, and exfiltration.

**Possible data sources**

- Public DGA datasets.
- Public DNS tunneling datasets.
- Malware traffic PCAPs converted to Zeek `dns.log`.
- Benign domain lists with careful leakage control.

**Technical components**

- Domain lexical features: length, entropy, digit ratio, consonant ratio, n-grams, subdomain depth.
- Host-level aggregation: NXDOMAIN ratio, query volume, unique domains, TTL patterns, rare TLDs.
- Models: LightGBM/XGBoost baseline, char-CNN, BiLSTM, small Transformer, anomaly detection by host.
- Evaluation: family/tool holdout, time split, domain leakage checks.
- Deployment: threshold tied to analyst review budget.

**Expected deliverables**

- DNS feature pipeline.
- Model comparison between tree models and a character-level neural model.
- Family-holdout evaluation to test generalisation.
- Detection runbook for suspicious host/domain investigation.

**Portfolio value**

High. It shows protocol understanding, practical feature engineering, and a meaningful place for DL.

---

### Project C: BGP Route Leak / Hijack / Outage Anomaly Monitor

**Short description**

Use public BGP data to detect routing anomalies such as origin changes, route leaks, excessive withdrawals, MOAS events, and prefix instability.

**Why this complements project 1**

This is the strongest IP networking project. It demonstrates internet routing knowledge rather than only security ML. It is also rare in typical ML/security portfolios.

**Possible data sources**

- RouteViews.
- RIPE RIS.
- CAIDA AS relationship data.
- RPKI/ROA validation sources.
- Public incident timelines for known leaks/hijacks.

**Technical components**

- BGP update parsing.
- Features: AS path length, origin AS changes, prefix churn, withdrawal bursts, MOAS, AS relationship violations, RPKI validity.
- Models: EWMA/change-point baselines, Isolation Forest, sequence autoencoder, graph-based anomaly features.
- Incident replay: reconstruct known BGP events and compare detection latency.

**Expected deliverables**

- Time-series anomaly pipeline.
- Incident timeline report.
- Visualisation of prefix/origin/AS-path changes.
- Clear explanation of what ML adds over deterministic routing checks.

**Portfolio value**

Very high for network engineering credibility. Higher implementation risk than DNS or Zeek because BGP data parsing and ground truth are harder.

---

### Project D: Encrypted Traffic / TLS Metadata Detection

**Short description**

Use TLS and connection metadata rather than packet payloads to identify suspicious encrypted traffic, malware communication patterns, or application classes.

**Why this complements project 1**

Modern networks are encrypted. This project shows practical constraints: privacy, lack of payload, changing TLS fingerprints, certificate metadata, and drift.

**Possible data sources**

- Zeek `ssl.log`, `x509.log`, `conn.log` extracted from public malware PCAPs.
- Public encrypted traffic classification datasets.
- Malware traffic samples where licensing permits.

**Technical components**

- TLS metadata: SNI, certificate issuer/subject, validity period, self-signed flag, JA3/JA4 where available.
- Flow metadata: duration, bytes, packets, directionality, periodicity.
- Models: LightGBM/XGBoost baseline, autoencoder, sequence model for host sessions.
- Privacy-aware design: avoid relying on payload or user-sensitive content.
- Drift monitoring: browser/TLS ecosystem changes can break fingerprint assumptions.

**Expected deliverables**

- TLS metadata feature matrix.
- Evaluation report on known malware vs benign or suspicious vs normal traffic.
- Privacy and drift note.
- Triage guide explaining how an analyst would investigate a suspicious TLS flow.

**Portfolio value**

High. Good bridge between network security and applied ML, but must avoid overclaiming because public labelled datasets can be messy.

---

### Project E: Cloud / VPC Flow Logs Detection Pipeline

**Short description**

Build a cloud network detection pipeline around VPC Flow Logs or equivalent flow telemetry, including scan detection, unusual egress, suspicious ports, and ML-based anomaly triage.

**Why this complements project 1**

Cloud security is an employable direction. This project converts NetFlow-style thinking into a modern cloud environment and adds infrastructure, monitoring, and detection-as-code.

**Possible data sources**

- Public AWS/Azure/GCP flow log examples.
- Simulated lab traffic in a small local/cloud lab.
- Synthetic VPC Flow Logs generated from controlled scenarios.

**Technical components**

- Flow log parser.
- Rule detections: port scan, unusual egress, new geo/ASN, denied connection spikes.
- ML anomaly model for source/destination behaviour.
- IaC or local simulation if real cloud use is not desired.
- Alert output compatible with SIEM-style JSON.

**Expected deliverables**

- Detection pipeline with config-driven rules.
- Example alerts and triage runbooks.
- Dashboard or notebook showing alert volume and false-positive assumptions.
- Optional Docker Compose / local generator.

**Portfolio value**

High for employability. Less research depth, more engineering and cloud-security realism.

---

### Project F: IoT Device Fingerprinting and Unauthorized Device Detection

**Short description**

Profile devices from network behaviour and detect unknown or misbehaving devices using traffic metadata, DNS, protocol usage, periodicity, and behavioural fingerprints.

**Why this complements project 1**

It shifts from attack classification to asset and behaviour modelling, which is closer to enterprise network operations and Zero Trust/NAC use cases.

**Possible data sources**

- IoT-23.
- Public IoT device identification datasets.
- CICIoT/CICIoMT datasets if access and license are acceptable.

**Technical components**

- Device behavioural profile: ports, destinations, DNS patterns, flow timing, protocol mix.
- Classification of known device types.
- Open-set or anomaly detection for unknown devices.
- Drift: firmware updates and cloud endpoint changes.

**Expected deliverables**

- Device fingerprinting report.
- Unknown-device detection experiment.
- Operational notes: how this would support asset inventory or NAC.

**Portfolio value**

Medium to high. Strong practical story if framed as asset security, weaker if it becomes just another IoT dataset classifier.

---

### Project G: Insider Threat / Lateral Movement Graph and Sequence Detection

**Short description**

Use authentication and host logs to detect suspicious user-host behaviour, lateral movement patterns, and insider-risk sequences.

**Why this complements project 1**

It adds identity, graph analytics, temporal sequences, and SIEM-style telemetry. It is less IP-network focused but highly relevant to security data science.

**Possible data sources**

- LANL authentication logs.
- CERT Insider Threat.
- Mordor / OTRF security datasets.
- Splunk BOTS-style data.

**Technical components**

- User-host graph construction.
- Temporal features: rare logon paths, privilege changes, fan-out, after-hours activity.
- Models: graph features + LightGBM, node embeddings, temporal graph model, sequence model.
- Evaluation with alert budget and analyst triage constraints.

**Expected deliverables**

- User-host graph pipeline.
- Suspicious path visualisation.
- ML triage model and rule baseline.
- Investigation notes for sample alerts.

**Portfolio value**

High for SOC/security data science roles. Lower direct IP networking signal, but good complement after a network-heavy project.

---

### Project H: Adversarial Robustness for Network Detectors

**Short description**

Extend `01-honest-nids` by testing whether flow-based detectors can be evaded under realistic network constraints, then compare naive adversarial attacks with feasible attacker actions.

**Why this complements project 1**

It deepens the existing project rather than creating a new domain. It is useful if targeting adversarial ML or AI security roles.

**Possible data sources**

- Existing `01-honest-nids` NetFlow datasets.
- Malware/NIDS benchmark datasets already prepared.

**Technical components**

- Define realistic feature constraints: packet counts, byte counts, duration, directionality.
- Compare unconstrained perturbations vs physically plausible perturbations.
- Evaluate evasion success, detector robustness, and adversarial training.
- Discuss why many academic adversarial attacks are not operationally realistic.

**Expected deliverables**

- Threat model document.
- Evasion experiment notebook.
- Robustness matrix by model and feature group.
- Clear conclusion on what attacks are realistic.

**Portfolio value**

Medium to high. Strong theory and rigor, but less helpful for fixing the "not deployable enough" weakness unless paired with a telemetry project.

---

## 4. Initial Prioritisation Matrix

Scoring scale: 1 = weak, 5 = strong.

| Candidate | Network depth | ML/DL depth | Security engineering realism | Data feasibility | Portfolio distinctiveness | Implementation risk | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|
| A. Zeek + ATT&CK Detection Lab | 5 | 4 | 5 | 4 | 5 | 3 | 5 |
| B. DNS Tunneling / DGA | 4 | 5 | 4 | 4 | 4 | 2 | 4 |
| C. BGP Anomaly Monitor | 5 | 4 | 4 | 3 | 5 | 5 | 4 |
| D. TLS Metadata Detection | 4 | 4 | 4 | 3 | 4 | 3 | 4 |
| E. Cloud / VPC Flow Logs | 4 | 3 | 5 | 3 | 4 | 3 | 4 |
| F. IoT Fingerprinting | 4 | 4 | 4 | 4 | 3 | 3 | 3 |
| G. Insider / Lateral Movement | 3 | 5 | 5 | 4 | 4 | 4 | 4 |
| H. Adversarial NIDS Robustness | 3 | 5 | 3 | 5 | 4 | 3 | 3 |

Interpretation:

- Best immediate next project: **A. Zeek + ATT&CK Detection Engineering Lab**.
- Best ML/DL-heavy follow-up: **B. DNS Tunneling / DGA**.
- Best IP networking differentiator: **C. BGP Anomaly Monitor**.
- Best employability/cloud angle: **E. Cloud / VPC Flow Logs**.

---

## 5. Recommended Portfolio Shape

### Core portfolio narrative

1. **Project 1: Honest NIDS**
   - Message: I understand why benchmark NIDS results are often misleading.
   - Strength: rigorous evaluation, leakage control, LODO, base-rate thinking.

2. **Project 2: Zeek + ATT&CK Detection Engineering Lab**
   - Message: I can build detections from real network telemetry and map them to attacker behaviour.
   - Strength: security engineering, logs, rules, ML-assisted triage, analyst workflow.

3. **Project 3: DNS Tunneling / DGA Detection**
   - Message: I can build a protocol-aware detector with both classical ML and DL.
   - Strength: DNS semantics, lexical modelling, host aggregation, deployment thresholds.

4. **Project 4: BGP Anomaly Monitor**
   - Message: I have deeper IP networking knowledge than a normal ML candidate.
   - Strength: routing, AS paths, prefix events, internet-scale anomaly detection.

Optional depending on target roles:

- For cloud security roles: add **Cloud / VPC Flow Logs Detection Pipeline**.
- For AI security/adversarial ML roles: add **Adversarial NIDS Robustness**.
- For SOC/data science roles: add **Insider Threat / Lateral Movement Graph Detection**.

---

## 6. Recommended Next Project: Zeek + ATT&CK Detection Engineering Lab

This should be the default next project because it directly repairs the main weakness of `01-honest-nids`: lack of deployable security engineering context.

### Proposed working title

`02-zeek-attack-detection-lab`

### MVP scope

- Pick 3 to 5 public PCAP scenarios.
- Convert them to Zeek logs.
- Build a small feature pipeline from `conn.log`, `dns.log`, `http.log`, `ssl.log`.
- Implement 5 to 10 detection hypotheses.
- Map each detection to ATT&CK where appropriate.
- Add a simple anomaly model for host/session prioritisation.
- Produce alert examples with triage notes.

### Research-grade extension

- Compare rule-only, ML-only, and hybrid detection.
- Add alert budget analysis.
- Add drift or cross-scenario generalisation test.
- Add Suricata alerts as another signal source.
- Build a small review UI or static alert report.

### What would make it strong in interviews

- Explain why a detection exists before showing the model.
- Show which telemetry field supports the detection.
- Explain false positives and how an analyst would triage them.
- Discuss alert volume, thresholding, and base-rate constraints.
- Be honest about dataset limitations and what would change in production.

---

## 7. Source Leads to Verify

These are useful starting points for formal citations and implementation research. Each should be checked again before final project documentation.

- NIST Cybersecurity Framework 2.0: https://www.nist.gov/cyberframework
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- MITRE ATT&CK Detection Strategies: https://attack.mitre.org/detectionstrategies/
- MITRE ATT&CK Network Traffic data source: https://attack.mitre.org/datasources/DS0029/
- Zeek logs documentation: https://docs.zeek.org/en/current/logs/index.html
- Malware-Traffic-Analysis.net: https://www.malware-traffic-analysis.net/
- Stratosphere IPS datasets: https://www.stratosphereips.org/datasets-overview
- RouteViews: https://www.routeviews.org/
- RIPE RIS: https://ris.ripe.net/
- LANL cyber security datasets: https://csr.lanl.gov/data/
- OTRF Security Datasets / Mordor: https://github.com/OTRF/Security-Datasets

---

## 8. Immediate Next Actions

1. Decide whether project 2 should be Zeek/ATT&CK, DNS, or BGP.
2. For the chosen project, write a one-page project proposal:
   - problem statement
   - target role signal
   - telemetry source
   - data sources
   - MVP deliverables
   - evaluation plan
   - expected limitations
3. Build a reading list with only the minimum papers/docs needed to start.
4. Create the project directory and first reproducible pipeline.

Current recommendation: start with **`02-zeek-attack-detection-lab`**, then follow with DNS or BGP depending on whether the next target is security analytics/ML or IP networking depth.
