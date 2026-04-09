# Existing Sections

Physics-Informed State Projection: A Trajectory-Based Spatiotemporal Kernel Method for Scalable Traffic Forecasting

1. Introduction

1.1 Background: The Imperative of Predictive Management

Rapid urbanization and the proliferation of Intelligent Transportation Systems (ITS) have placed unprecedented demands on real-time traffic management. Short-term traffic flow prediction, which forecasts traffic states (e.g., volume, speed) for the upcoming 15 to 60 minutes, serves as the fundamental engine for proactive congestion control and dynamic route guidance. Accurate and timely predictions allow traffic operators to transition from "reactive response" to "active management," significantly optimizing the operational efficiency of urban road networks.

1.2 The Gap: Between "Black-Box" Accuracy and Physical Interpretability

Existing prediction methodologies generally fall into two categories: model-driven and data-driven approaches.

Model-driven approaches, such as kinematic wave theory and queuing models (Lighthill & Whitham, 1955), rely on explicit physical laws governing flow dynamics. While highly interpretable, these methods often struggle to scale to large, complex urban networks due to rigid assumptions and difficulties in real-time parameter calibration.

- Data-driven approaches, particularly recent Deep Learning (DL) models like Long Short-Term Memory (LSTM) networks and Graph Convolutional Networks (GCN), have achieved state-of-the-art prediction accuracy by mining non-linear spatiotemporal patterns. However, these models typically operate as "black boxes." They learn implicit weight matrices that lack physical meaning, making it difficult to trace the causality of traffic evolution. For instance, when a GCN predicts a congestion peak, it is often unclear whether this arises from upstream propagation or local demand surges. This lack of explainability hinders their adoption in safety-critical traffic engineering scenarios where understanding the "why" is as important as the "what."

1.3 The Proposed Solution: A Physics-Informed Data-Driven Framework

To bridge this gap, this study proposes a novel Data-Driven Spatiotemporal Propagation Framework for short-term traffic prediction. Unlike pure deep learning models that blindly fit data correlations, our approach treats traffic prediction as a physical propagation process constrained by the network topology. We utilize massive historical floating car data (trajectory sequences) not to train a neural network, but to explicitly calibrate the kinetic parameters of the road network.

The core innovation lies in the construction of a "White-Box" inference engine. We extract three fundamental kernels—Average Travel Time, Flow Transition, and Upstream Contribution—from vehicle trajectories to quantify the dynamic correlations between nodes. Based on these explicit parameters, we design a rolling horizon algorithm that simulates how traffic waves "propagate" from upstream to downstream nodes with specific time lags, akin to a fluid dynamic process but powered by real-world data.

1.4 Contributions

The main contributions of this paper are summarized as follows:

Methodological Innovation: We propose a probabilistic parameter extraction method that transforms microscopic vehicle trajectories into macroscopic network kernels, effectively quantifying the spatiotemporal impedance and transition probabilities between road nodes.

Algorithm Design: We develop an explicit spatiotemporal propagation algorithm featuring a soft temporal alignment kernel. This mechanism addresses the challenge of asynchronous traffic arrival and flow dispersion, offering superior interpretability compared to traditional recurrent neural networks.

System Realization: The proposed model is integrated into a closed-loop engineering architecture, demonstrating its capability to capture traffic evolution mechanics in a real-world urban environment.

2. Related Work

Existing literature on short-term traffic flow prediction is extensive. Historically, methodologies can be broadly categorized based on their underlying mechanisms into two distinct eras: classical parametric/non-parametric models and modern deep learning approaches.

2.1 Traditional Parametric and Non-Parametric Approaches

Early research was characterized by the dichotomy between statistical theories, which capture temporal patterns, and physical heuristics, which aim to replicate flow dynamics.

2.1.1 Time-Series and Statistical Models

The most prominent representatives of this category are the Auto-Regressive Integrated Moving Average (ARIMA) family. As reviewed by Van Arem et al. (1997), these models hypothesize that traffic flow evolves as a linear stationary process. Williams (1999) advanced this domain by introducing Seasonal ARIMA (SARIMA), which applies seasonal differencing to address the inherent weekly periodicity of traffic data (Wold decomposition). Due to their rigorous statistical foundation, these models became the industry standard for single-point forecasting.

Limitations: The applicability of ARIMA-based models is fundamentally constrained by their linear and stationary assumptions. As noted by Vlahogianni et al. (2004), they fail to capture the highly non-linear dynamics of traffic flow, such as the formation and propagation of shockwaves during congestion. Furthermore, these models typically treat each sensor as an isolated time series, ignoring the spatial topology of the road network and the interactive dependencies between upstream and downstream flows.

2.1.2 Physics-Based and State-Space Models

Parallel to statistical methods, researchers have attempted to integrate traffic flow theory into prediction via state-space formulations. A classic approach involves Kalman Filtering (KF), which links unobservable state variables to roadside observations (Whittaker et al., 1997). More sophisticated approaches utilize Dynamic Traffic Assignment (DTA) logic to estimate Origin-Destination (OD) flows and simulate driver behavior under control strategies. These methods explicitly incorporate physical relationships (e.g., the fundamental diagram) between speed, flow, and density.

Limitations: While offering high interpretability, these models suffer from the "Calibration Dilemma." They rely heavily on idealized boundary conditions and hard-to-obtain inputs (e.g., real-time dynamic OD matrices). As highlighted in classic studies, while physics-based updates improve accuracy during incidents, the complexity of calibrating global network dynamics in real-time restricts their scalability and robustness in noisy urban environments.

2.1.3 Early Non-Parametric and Pattern-Based Methods

To overcome the rigidity of parametric assumptions, non-parametric approaches were developed to "let the data speak." k-Nearest Neighbors (k-NN) regression, pioneered by Smith et al. (2002), predicts future states by searching for analogous historical patterns based on feature distance. These methods demonstrated that simple pattern recognition could outperform naive forecasts in short horizons by adapting to recurrent events. Early shallow Neural Networks also emerged during this period as universal non-linear regressors.

Limitations: Despite their flexibility, these methods face the "Curse of Dimensionality" when applied to large-scale networks. Crucially, algorithms like k-NN rely on statistical similarity in feature space rather than physical connectivity in topological space, making them unable to explicitly model the spatiotemporal propagation of traffic states (e.g., how a bottleneck propagates upstream).

2.2 Modern Deep Learning and Graph-Based Approaches

In recent years, the paradigm of traffic forecasting has shifted from statistical methods to Deep Learning (DL), with Graph Neural Networks (GNNs) emerging as the dominant framework. Unlike traditional Convolutional Neural Networks (CNNs) restricted to Euclidean grids, GNNs are designed to process non-Euclidean topologies, making them theoretically suitable for complex road networks.

2.2.1 Spatial Dependency Modeling

The foundational breakthrough lies in redefining the convolution operation on graphs to capture spatial correlations. Kipf & Welling (2017) proposed the Graph Convolutional Network (GCN), which approximates spectral convolution via first-order Chebyshev polynomials, allowing efficient feature aggregation from local neighbors. To address the limitations of static weights, Veličković et al. (2018) introduced Graph Attention Networks (GAT), employing self-attention mechanisms to dynamically assign importance weights to different neighbors. While these methods excel at capturing static spatial correlations, they inherently treat traffic nodes as abstract vertices, often overlooking the anisotropic nature of traffic flow (i.e., the distinct influence of upstream inflow versus downstream congestion).

2.2.2 Spatiotemporal Fusion Frameworks

Since traffic flow is inherently dynamic, pure spatial GNNs are typically integrated with temporal sequence modules. A seminal work is the Diffusion Convolutional Recurrent Neural Network (DCRNN) (Li et al., 2018), which models traffic as a diffusion process on a directed graph. By integrating diffusion convolution into the GRU gating mechanism, DCRNN captures the stochastic nature of traffic states. Subsequently, Wu et al. (2019) developed Graph WaveNet, combining graph convolutions with dilated causal convolutions to expand the receptive field exponentially. This architecture captures long-range temporal dependencies without the sequential computation bottleneck of RNNs. These "ST-GNN" frameworks currently represent the state-of-the-art in prediction accuracy.

2.2.3 Dynamic Structure Learning

Recognizing that the pre-defined physical topology may not fully reflect dynamic traffic correlations (e.g., ghost jams or hidden dependencies), recent research focuses on Structure Learning. Dynamic Graph Neural Networks (Bai et al., 2020; Chen et al., 2020) employ adaptive mechanisms to evolve the adjacency matrix at each time step. Multi-view GNNs (Lv et al., 2020) further fuse heterogeneous graphs—such as physical connectivity, POI similarity, and traffic pattern proximity—to learn latent spatial dependencies beyond simple road connections.

2.2.4 Critical Limitations: The "Black-Box" Barrier

Despite their superior performance on benchmark datasets, these deep learning models face critical challenges that hinder their deployment in safety-critical engineering systems:

The Interpretability and Causality Deficit: Complex architectures like DCRNN or Adaptive GNNs operate as "Black Boxes." They learn implicit weight matrices that minimize statistical error but lack physical correspondence. When a model predicts a congestion peak, it is mathematically opaque whether this result stems from upstream wave propagation or a learned temporal artifact. This lack of transparency is unacceptable for traffic operators who require actionable, causal insights (e.g., "congestion is caused by the bottleneck at node i").

Physical Inconsistency: Most GNNs treat traffic flow purely as numerical vectors, ignoring fundamental conservation laws and the flow-density-speed relationship. Consequently, they tend to "over-smooth" predictions, failing to capture sharp shockwaves caused by accidents or sudden capacity drops, as the loss functions (e.g., MSE) favor mean-reversion.

Computational Scalability: Models involving dynamic graph learning or multi-head attention scale quadratically with the network size (O(N²)). Calculating and updating a dense adjacency matrix for a city-wide network with thousands of links is computationally prohibitive for real-time applications.

2.3 Physics-Informed and Hybrid Approaches

While deep learning excels in pattern matching, it often neglects the conservation laws and causality governing traffic flow. To bridge this gap, recent research has pivoted towards Physics-Informed Machine Learning (PIML), aiming to synergize explicit traffic flow theories with data-driven expressiveness.

2.3.1 Classical Traffic Flow Theory: The Foundation

The theoretical bedrock of traffic dynamics is the Lighthill-Whitham-Richards (LWR) model (Lighthill & Whitham, 1955), which conceptualizes traffic as a compressible fluid governed by the continuity equation ($$\frac{\partial q}{\partial x} + \frac{\partial \rho}{\partial t} = 0$$). To implement this numerically on networks, Daganzo (1994, 1995) proposed the Cell Transmission Model (CTM), a discrete approximation that simulates flow propagation based on the Fundamental Diagram (FD). Higher-order phenomena, such as stop-and-go waves, are captured by models like Aw-Rascle-Zhang (ARZ) (Aw & Rascle, 2000), which introduce momentum equations to resolve theoretical inconsistencies like "negative velocity."

Limitations: Although these models offer perfect physical transparency, they are inherently deterministic and struggle to assimilate the high-frequency stochastic noise present in real-world data. Moreover, calibrating critical parameters (e.g., jam density, shockwave speed) for city-wide networks is an ill-posed inverse problem that is notoriously difficult to solve in real-time.

2.3.2 Physics-Guided Learning Frameworks

To combine the interpretability of theory with the adaptability of learning, hybrid frameworks have emerged, generally falling into two categories:

Physics-Regularized Learning (Soft Constraints): The dominant paradigm, popularized by Physics-Informed Neural Networks (PINNs) (Raissi et al., 2019), incorporates physical residuals directly into the loss function ($$J=J_{data} +\lambda J_{physics}$$). For traffic, Huang & Agarwal (2022) applied this to constrain traffic state estimation using the LWR conservation law. This forces the neural network to explore a solution space that is physically plausible, even with sparse data.

Physics-Augmented Learning (Feature Fusion): Another stream feeds outputs from theoretical models as augmented features into neural networks. Zhang et al. (2023) utilized simulation data from METANET to guide a DL predictor, while Yao et al. (2023) developed a Physics-Aware Learning (PAL) framework that explicitly calculates shockwave velocities to correct LSTM predictions, significantly reducing spatial errors in congested scenarios.

2.3.3 The Remaining Gap: From Constraint to Architecture

Despite these advances, a critical methodological gap remains for large-scale network prediction:

"Black Box with Handcuffs": Most PIML methods use physics merely as a soft constraint (Loss) or an external feature. The core predictor remains a neural network (Black Box). While the output is regularized, the internal inference process (matrix weights) remains uninterpretable. It is still difficult to trace how a specific upstream perturbation propagates to a downstream node within the network layers.

Computational Scalability: Embedding Partial Differential Equations (PDEs) or iterative numerical solvers (like CTM) within the training loop of a neural network entails a heavy computational burden. Solving high-dimensional derivatives for thousands of road links is often prohibitive for real-time online applications.

Lack of Network-Wide Propagation Logic: Existing PIML methods predominantly focus on single-link or corridor-level dynamics (e.g., estimating density on a highway segment). There is a scarcity of frameworks that explicitly model network-level propagation—how congestion spills over complex topologies—while retaining the intrinsic transparency of mechanism-based models.

This study aims to fill this gap. Unlike existing PIML methods that apply physics as an external patch, we construct the prediction architecture itself based on the physical propagation mechanism (Spatiotemporal Dispersion). By deriving the transition and impedance kernels directly from data, our model achieves the intrinsic interpretability of physical models and the scalability of data-driven methods.


---
3. Methodology

3.1 Framework Overview

This paper formulates a hierarchical short-term traffic flow prediction model designed to capture the spatiotemporal evolution of traffic states. The proposed framework integrates data-driven parameter estimation with physical propagation mechanisms, forming a closed-loop process characterized as “Data-Driven Calibration – State Propagation – Operational Implementation.”

The architectural logic utilizes the static road network topology as the structural backbone, upon which dynamic trajectory data are mapped as time-dependent state variables. The framework extracts network characteristics via the modeling layer, simulates the spatiotemporal propagation of traffic flow in the prediction layer, and aggregates nodal states into link-level metrics for deployment. The specific functions of the constituent modules are defined as follows:

- Data Acquisition and Preprocessing: Responsible for the ingestion and normalization of raw trajectory data, providing standardized inputs for the modeling process.

- Network Representation (Core Modeling): Constructs the graph-based topology and estimates three core parameter matrices to quantify spatiotemporal correlations between nodes.

- State Propagation (Prediction Algorithm): Executes multi-step rolling horizon predictions based on the calibrated matrices and defined propagation mechanisms.

- Macroscopic Aggregation (Post-processing): Maps node-level predictions to section-level metrics (e.g., saturation) and performs data rectification.

- Data Archiving and Service: Manages the persistence of prediction results and provides interfaces for external applications.

- Process Control: Ensures the stability of the model execution under high-frequency cycles.

The information flow within the framework is categorized into two streams:

- Static Topological Constraints: Static Network Data $$\to$$ Topology Mapping / Capacity Parameters $$\to$$ Network Representation Layer.

- Dynamic State Evolution: Trajectory Data $$\to$$ Standardized Path Sequences / Node Flow $$\to$$ Network Representation $$\to$$ State Propagation $$\to$$ Predicted Node States $$\to$$ Macroscopic Aggregation $$\to$$ Section Flow / Saturation.

3.2 Preliminaries and Problem Formulation

To rigorously characterize the spatiotemporal evolution of traffic flow, we first formalize the network topology and the dynamic state variables. This section details the abstraction of static physical constraints and the reconstruction of continuous vehicle trajectories into discrete network states.

3.2.1 Static Network Representation

The road network is modeled as a directed graph $$\mathcal{G} = (\mathcal{V}, \mathcal{E})$$, where $$\mathcal{V} = \{v_1, v_2, ..., v_N\}$$ denotes the set of $$N$$ intersections (nodes), and $$\mathcal{E} \subseteq \mathcal{V} \times \mathcal{V}$$ represents the set of connecting road segments (links). An edge $$e_{ij} = (v_i, v_j) \in \mathcal{E}$$ indicates a permissible traffic movement from node $$i$$ to node$$j$$.

Physical constraints are quantified by the node capacity, which bounds the maximum throughput. In this study, the theoretical capacity $$C_{i}$$ for node $$v_i$$ is estimated based on the connecting lane configurations. Following the underlying logic of intersection saturation flow, this is formulated as:

$$C_{i} = \kappa \cdot \phi(L_i) \quad (1) $$

where $$L_i$$ represents the aggregate lane features associated with node $$i$$, $$\phi(\cdot)$$ is a geometric mapping function, and $$\kappa$$ denotes the saturation flow parameter (calibrated as 1625 pcu/h). These static attributes define the boundary conditions for the dynamic system.

3.2.2 Temporal Discretization and State Reconstruction

Raw trajectory data, comprising asynchronous GPS sequences, are mapped onto the topological graph $$\mathcal{G}$$ to generate synchronized traffic states.

The time domain is discretized into uniform intervals of length $$\Delta t$$ (set to 15 minutes), yielding a discrete time sequence $$\mathcal{T} = \{t_1, t_2, \dots, t_M\}$$, where $$M$$ denotes the total time steps in a daily cycle.

Trajectory Mapping and Continuity:

A vehicle trajectory is defined as a spatiotemporal path $$P_k$$. To transform these continuous paths into discrete node states, we employ a map-matching algorithm that projects coordinates onto the nearest valid logical links in $$\mathcal{G}$$. To ensure the physical continuity of traffic flow (conservation of vehicles), trajectory gaps are reconstructed via linear interpolation under the assumption of uniform travel speed between observed control points.

Traffic State Definition:

Based on the reconstructed trajectories, we define thetraffic flow tensor$$\mathbf{X} \in \mathbb{R}^{N \times M}$$, where each entry $$x_{i,t}$$ represents the aggregate volume traversing node $$v_i$$ during time interval$$t$$. This structured state variable serves as the fundamental input for the subsequent propagation modeling.

3.3 Spatiotemporal Parameter Extraction

This section delineates the data-driven mechanism for extracting the intrinsic dynamic characteristics of the road network. Unlike black-box models that implicitly learn weights, our framework explicitly quantifies the spatiotemporal correlations between nodes by constructing three fundamental parameter matrices: Average Travel Time Matrix, Flow Transition Matrix, and Upstream Contribution Matrix. These matrices are derived by aggregating historical vehicle trajectories over the graph $$\mathcal{G}$$.

3.3.1 Micro-to-Macro Aggregation Mechanism

The parameter extraction is grounded in two intermediate accumulation matrices, initialized as zero matrices of size $$N \times N$$: the$$\mathbf{E}^F$$Edge Flow Matrix () and the $$\mathbf{E}^T$$Edge Time Matrix ().

For every valid vehicle trajectory $$P_k = \{(v_{s}, \tau_{s}), \dots, (v_{e}, \tau_{e})\}$$, we analyze the transitions between any pair of visited nodes $$(v_i, v_j)$$ in the sequence, encompassing both direct adjacencies and multi-hop indirect connections.

- Flow Accumulation:$$\mathbf{E}^F_{ij} \leftarrow \mathbf{E}^F_{ij} + 1$$, representing the frequency of connectivity from $$i$$ to $$j$$.

- Time Accumulation:$$\mathbf{E}^T_{ij} \leftarrow \mathbf{E}^T_{ij} + (\tau_j - \tau_i)$$, accumulating the total travel cost. Temporal validity checks are enforced to discard anomalies where$$\tau_j \le \tau_i$$ (logic violation). This aggregation process, illustrated in Figure 2, effectively maps massive discontinuous trajectory data into structured network-wide statistics.

[Insert Figure 2: Data-Driven Modeling & Matrix Construction Process]

3.3.2 Derivation of Core Propagation Matrices

Based on the accumulated statistics, we derive the three core matrices that govern the traffic propagation dynamics.

(1) Average Travel Time Matrix ($$\mathbf{T}$$)

This matrix quantifies the temporal impedance between node pairs. Each entry $$T_{ij}$$ represents the expected travel time (in minutes) for a vehicle to propagate from node $$i$$ to node $$j$$. It is computed by the element-wise division of the time accumulation and flow accumulation matrices:

$$T_{ij} = \begin{cases} \frac{\mathbf{E}^T_{ij}}{\mathbf{E}^F_{ij}}, & \text{if } \mathbf{E}^F_{ij} > 0 \\ \infty, & \text{otherwise} \end{cases} \quad (2)$$

where$$\infty$$ denotes no historical connectivity. $$T_{ij}$$ serves as the critical parameter for the time-lag estimation in the propagation model.

(2) Flow Transition Matrix ($$\mathbf{D}$$)

The Transition Matrix$$\mathbf{D}$$ describes the probabilistic distribution of traffic routing choices. Analogous to a Markovian transition matrix, $$D_{ij}$$ signifies the conditional probability that a vehicle at node $$i$$ will travel to node $$j$$. It is obtained by row-normalizing the Edge Flow Matrix:

$$D_{ij} = \begin{cases} \frac{\mathbf{E}^F_{ij}}{\sum_{k=1}^N \mathbf{E}^F_{ik}}, & \text{if } \sum_{k=1}^N \mathbf{E}^F_{ik} > 0 \\ 0, & \text{otherwise} \end{cases} \quad (3)$$

This matrix captures the downstream splitting behavior of traffic flow.

(3) Upstream Contribution Matrix ($$\mathbf{C}$$)

While $$\mathbf{D}$$ looks forward, the Contribution Matrix $$\mathbf{C}$$ looks backward to trace the origins of traffic flow. $$C_{ij}$$ quantifies the proportion of flow at target node $$j$$ that originated from upstream node $$i$$. This is derived by column-normalizing the Edge Flow Matrix:

$$C_{ij} = \begin{cases} \frac{\mathbf{E}^F_{ij}}{\sum_{k=1}^N \mathbf{E}^F_{kj}}, & \text{if } \sum_{k=1}^N \mathbf{E}^F_{kj} > 0 \\ 0, & \text{otherwise} \end{cases} \quad (4)$$

$$\mathbf{C}$$ is pivotal for identifying significant upstream sources and weighting their influence in the prediction algorithm.

3.4 Spatiotemporal Propagation Prediction Algorithm

The core inference engine adopts a Physics-Informed State Projection Strategy. Unlike black-box models that perform implicit feature mapping, this module explicitly simulates the propagation of traffic waves across the network graph $$\mathcal{G}$$. It leverages the calibrated kernels ($$\mathbf{T}, \mathbf{D}, \mathbf{C}$$) to project the evolution of flow dynamics over future horizons.

3.4.1 Prediction Problem Formulation

We formulate the task as a multi-step sequence generation problem. Given the historical traffic state at current time $$t_0$$, the objective is to predict the flow state vectors for the next $$H$$ horizons: $$\hat{\mathbf{Q}} = \{\mathbf{q}^{(1)}, \mathbf{q}^{(2)}, \dots, \mathbf{q}^{(H)}\}$$, where $$\mathbf{q}^{(\tau)} \in \mathbb{R}^N$$ denotes the predicted flow intensity at time $$t_0 + \tau \cdot \Delta t$$.

To mitigate high-frequency stochastic noise, the initial state $$\mathbf{q}^{(0)}$$ is established via a smoothing filter over the immediate past window:

$$\mathbf{q}^{(0)}_i = \frac{1}{3} \sum_{k=0}^2 x_{i, t_0 - k} \quad (5) $$

This smoothed state serves as the propagation source, emitting traffic waves that travel through the network topology.

3.4.2 Temporal Alignment and Wave Propagation

The fundamental challenge is handling the asynchronous arrival of traffic flow due to heterogeneous travel times. We address this by modeling the discrete time lag using a Triangular Temporal Kernel, which functions as a discrete impulse response function.

For a target node $$j$$ and a prediction horizon $$\tau$$, we consider the set of effective upstream neighbors $$U_j = \{v_i \in \mathcal{V} \mid C_{ij} \ge \theta\}$$. The flow propagation is modeled as follows:

(1) Temporal Alignment Kernel ($$W_{ij}$$)

Traffic propagation is governed by the expected delay $$T_{ij}$$. The kernel function $$\mathcal{K}(\cdot)$$ quantifies the synchronization intensity between the physical travel time and the prediction horizon $$\tau$$:

$$W_{ij}(\tau) = \mathcal{K}\left( \tau, \frac{T_{ij}}{\Delta t} \right) = \max\left( 0, 1 - \left| \frac{T_{ij}}{\Delta t} - \tau \right| \right) \quad (6) $$

Physically, this kernel represents the dispersion effect of traffic platoons: the arrival probability peaks when the prediction horizon aligns with the average travel time and decays linearly as the mismatch increases.

(2) Probabilistic Flow Transfer

The estimated flow contribution from upstream node $$i$$ to downstream node $$j$$ at horizon $$\tau$$, denoted as $$\hat{f}_{ij}(\tau)$$, is derived by projecting the initial state through the transition and temporal kernels:

$$\hat{f}_{ij}(\tau) = \underbrace{D_{ij} \cdot \mathbf{q}^{(0)}_i}_{\text{Routed Vol.}} \cdot \underbrace{W_{ij}(\tau)}_{\text{Temporal Prob.}} \quad (7) $$

This mechanism effectively scans the initial traffic distribution and "places" it into the appropriate future time slots at downstream locations.

[Insert Figure 3: Spatio-Temporal Propagation Mechanism]

3.4.3 Adaptive State Synthesis

To synthesize the multi-source contributions, we employ an adaptive fusion strategy that weights upstream inputs based on their structural importance and temporal validity. The fusion weight $$\omega_{ij}(\tau)$$ is defined as:

$$\omega_{ij}(\tau) = \frac{C_{ij}}{1 + \alpha \cdot \left( \frac{T_{ij}}{\Delta t} - \tau \right)^2} \quad (8) $$

where $$\alpha$$ is a decay hyperparameter. The quadratic denominator penalizes contributions that are temporally misaligned, ensuring that predictions are dominated by waves arriving precisely at the target horizon.

Finally, the predicted state intensity for node $$j$$ at step $$\tau$$ is computed via weighted synthesis:

$$\mathbf{q}^{(\tau)}_j = \frac{\sum_{v_i \in U_j} \hat{f}_{ij}(\tau) \cdot \omega_{ij}(\tau)}{\sum_{v_i \in U_j} \omega_{ij}(\tau) + \epsilon} \quad (9) $$

where $$\epsilon$$ is a small constant for numerical stability. This aggregation process mimics the superposition of traffic waves, resulting in a physically consistent prediction of network states.



4. Experiments

4.1 Dataset and Experimental Setup

To rigorously assess the fidelity of the proposed framework in capturing complex network dynamics, we conducted a large-scale empirical study utilizing high-resolution gantry data from the highway network of Shandong Province, China.

4.1.1 Data Description: The Shandong Highway Dataset

Unlike traditional Floating Car Data (FCD) derived from sparse GPS probes, which often suffer from low penetration rates and sampling bias, this study utilizes Automatic Vehicle Identification (AVI) data captured by the pervasive gantry system. This source provides precise, full-sample cross-sectional observations, ensuring that macroscopic flow conservation laws are observable. The specific characteristics are as follows:

(1) Topological Scale ($$\mathcal{G}$$): The study area encompasses the entire provincial highway network. The underlying graph $$\mathcal{G}=(\mathcal{V},\mathcal{E})$$ consists of approximately 4,800 directed road segments (edges), defined by consecutive gantry intervals. Notably, the network topology is not static; it undergoes minor dynamic permutations due to infrastructure maintenance and device updates during the observation window. Our graph-based formulation naturally accommodates these topological variations without requiring model retraining.

(2) Temporal Scope as a "Stress Test": Instead of routine weekdays dominated by recurrent patterns, we specifically selected four major holiday periods in 2024-2025: the Spring Festival, Tomb-Sweeping Day, Labor Day, and National Day. The total observation window spans approximately 30 days. These periods were selected to serve as a robust stress test, as they represent the most challenging regimes for traffic prediction characterized by oversaturated flow, non-stationary demand surges, and irregular shockwave propagation.

(3) Volume and Granularity: The dataset is exceptionally voluminous, recording a daily average of 30 million vehicle detection events. The cumulative dataset exceeds 900 million trajectory points, offering a granular view of macroscopic traffic evolution.

4.1.2 Data Sanitization and Trajectory Reconstruction

Raw gantry data, while comprehensive, requires rigorous preprocessing to transform discrete cross-sectional snapshots into continuous path flows consistent with our methodology (Section 3). The process involves three key steps:

(1) Data Sanitization: A filtering mechanism was applied to remove anomalies. Records with low recognition confidence or those implying physically impossible travel speeds (e.g., $$v>180$$ km/h, violating kinematic limits) were purged to eliminate measurement noise and ensure data quality.

(2) Trajectory Logic Reconstruction: Since gantries function as discrete observation nodes, we reconstructed the continuous spatiotemporal trajectory $$P_k$$ for each vehicle. Missing intermediate nodes were inferred based on the shortest path algorithm constrained by the closed highway topology and timestamp validity. This step ensures the topological continuity of vehicle movements, generating the complete node-visiting sequences required for the matrix extraction module.

(3) Macroscopic Aggregation: The validated trajectories were aggregated into uniform time intervals ($$\Delta t=15$$ min) to construct the dynamic flow tensors used for model calibration and validation.

4.2 Overall Performance Comparison

To evaluate the predictive fidelity and physical consistency of our proposed framework, we benchmarked our Trajectory-based Spatiotemporal Propagation Model (Proposed Model) against three representative baselines: Historical Average (HA), Auto-Regressive Integrated Moving Average (ARIMA, Time-Series), and Long Short-Term Memory (LSTM, Deep Learning). The evaluation was conducted on the Shandong highway dataset, focusing on a representative holiday peak window ("Window 40") characterized by dynamic congestion patterns.

Table 1 summarizes the performance metrics. In addition to the standard Weighted Mean Absolute Percentage Error (WAPE), we introduce Volume Bias (ratio of predicted total volume to ground truth) as a critical metric to assess whether the models adhere to the Law of Conservation of Traffic Flow.

Table 1: Performance Comparison on Holiday Traffic Prediction (Window 40)

Model Type

Model

Overall WAPE

Step 1 WAPE (15 min)

Step 6 WAPE (90 min)

Pred. Mean Flow

True Mean Flow

Volume Bias (Conservation)

Deep Learning

LSTM

0.224

0.216

0.237

327.28

347.06

94.3% (-5.7%)

Physics-Aware

Proposed Model

0.249

0.216

0.285

382.52

387.68

98.7% (-1.3%)

Statistical

HA

0.282

0.289

0.281

307.75

372.80

82.5% (-17.5%)

Time-Series

ARIMA

0.369

0.153

0.601

476.64

372.80

127.8% (+27.8%)

Analysis of Results:

(1) Macro-Level Flow Conservation (The Core Advantage):

While deep learning models excel at minimizing point-wise residuals (MSE/MAE), they often suffer from "Systematic Scale Drift." As evidenced in Table 1, LSTM underestimates the total network traffic volume by 5.7%, and HA severely underestimates it by 17.5% due to its inability to capture sudden demand surges. In stark contrast, our proposed model achieves a near-perfect volume bias of 98.7% (a negligible -1.3% deviation). This result validates that our architecture explicitly respects the trajectory conservation principle—i.e., flow is not arbitrarily generated or destroyed but propagates from upstream to downstream. This property is indispensable for macroscopic traffic management, where estimating the correct total magnitude of demand is often more critical than fitting minute-level fluctuations.

(2) Competitive Precision with "Zero-Shot" Efficiency:

In terms of predictive accuracy (WAPE), our model (0.249) performs comparably to the state-of-the-art LSTM (0.224), with the gap being marginal. Notably, for the immediate horizon (Step 1, 15-min), our model achieves a WAPE of 0.216, tying with LSTM and significantly outperforming the statistical baseline HA (0.289). It is crucial to highlight the efficiency trade-off: LSTM requires extensive GPU training, hyperparameter tuning, and iterative backpropagation. Conversely, our model operates in a "Training-Free" manner—it constructs the propagation kernels directly from historical trajectories without optimization loops. Achieving such competitive accuracy with a parameter-free, white-box approach represents a significant engineering breakthrough.

(3) Temporal Stability and Robustness:

The comparison with ARIMA highlights the importance of spatial modeling. ARIMA exhibits a typical "explosive" error pattern: while it excels at the very first step (0.153) due to strong autocorrelation, its error diverges rapidly to 0.601 by Step 6. Our model, leveraging spatiotemporal propagation logic, demonstrates temporal stability similar to LSTM, maintaining robust performance across multi-step horizons (0.216 to 0.285).

(4) Operational Adaptability:

Beyond numerical metrics, our proposed framework offers unique advantages for deployment in dynamic environments like the Shandong highway network, where gantries are frequently added or removed. Deep learning models like LSTM would require complete retraining to accommodate dimension changes in the input vector. In contrast, our graph-based model handles topology changes naturally by updating the trajectory lookup adjacency matrices, ensuring seamless maintenance and high scalability.

4.3 Ablation Study: Validating Physical Mechanisms

4.3.1 Ablation Experiment Design

To dissect the contribution of each module within our "White-Box" architecture, we conducted a rigorous ablation study. By selectively deactivating specific physical constraints, we evaluated three variants against our Standard Model: (a) No Temporal Kernel, which assumes instantaneous propagation ($$W_{ij}(\tau) \equiv 1$$); (b) No Upstream Matrix, which relies solely on a node's self-history; and (c) Static Weights, which applies off-peak parameters to peak-hour predictions. Table 2 summarizes the resulting performance degradation.

Table 2: Ablation Study Results

Comparison of WAPE and Degradation rates. "Degradation" indicates the relative performance drop compared to the Standard model.

Model Variant

Mechanism Removed

Overall WAPE

Step 1 WAPE (15 min)

Step 6 WAPE (90 min)

Degradation

Standard (Ours)

Full Physics

0.2779

0.2541

0.3028

-

No Upstream

Spatial Propagation

0.2914

0.2013

0.4097

+4.8%

Static Weights

Dynamic Update

0.3671

0.3260

0.3986

+32.1%

No Temporal

Time Lag

0.6745

0.6183

0.7260

+142.7%

4.3.2 Impact of Temporal Kernel on Causality and Conservation

The most catastrophic performance degradation was observed in the No Temporal Kernel variant, where the error skyrocketed by 142.7% (WAPE 0.6745). Physically, removing the time-alignment mechanism implies that vehicles departing from an upstream node arrive at the downstream location instantaneously. This assumption violates the fundamental principle of causality in traffic flow, leading to a severe phase mismatch. Consequently, traffic waves are superimposed onto the downstream node before they physically arrive, resulting in a significant overestimation of the total volume (Predicted: 482.6 vs. Ground Truth: 387.5). This empirical evidence confirms that the temporal kernel$$\mathcal{K}(\tau)$$ is not merely a numerical optimization trick but the fundamental "clock" of our framework, ensuring that mass conservation is respected over time.

4.3.3 Impact of Spatial Propagation and Dynamic Parameter Update

The analysis of spatial dependencies, represented by the No Upstream variant, reveals an insightful trade-off between local inertia and network propagation. In the immediate short-term (Step 1), the isolationist model outperforms our Standard model (0.2013 vs. 0.2541), suggesting that for the next 15 minutes, a node's self-inertia is the dominant predictor. Introducing upstream data at this stage imposes a slight "noise tax" due to stochastic fluctuations in arrival times. However, this advantage vanishes rapidly; as the prediction horizon extends to 90 minutes (Step 6), the performance of the isolationist model collapses to 0.4097. This confirms that long-term traffic evolution is governed by incoming waves from neighbors rather than self-history. Our Standard model successfully balances this trade-off, accepting a marginal cost in short-term precision to secure essential long-term robustness, which is the primary objective of network-level forecasting.

Finally, the experiment with Static Weights highlights the non-stationary nature of traffic dynamics. Using parameters derived from off-peak periods to predict peak-hour traffic resulted in a 32.1% performance drop. Traffic regimes evolve; the transition probabilities ($$D_{ij}$$) and travel speeds ($$T_{ij}$$) during free-flow conditions are fundamentally different from those under congestion. A static graph topology fails to capture this evolution. These results validate the necessity of our Dynamic Matrix Construction, which allows our model to re-calibrate its physical parameters in real-time, effectively adapting to the time-varying impedance of the road network.


