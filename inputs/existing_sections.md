# 2. Related Work

Existing literature on short-term traffic flow prediction is extensive. Historically, methodologies can be broadly categorized based on their underlying mechanisms into two distinct eras: classical parametric/non-parametric models and modern deep learning approaches.

## 2.1 Traditional Parametric and Non-Parametric Approaches

Early research was characterized by the dichotomy between statistical theories, which capture temporal patterns, and physical heuristics, which aim to replicate flow dynamics.

### 2.1.1 Time-Series and Statistical Models

The most prominent representatives of this category are the Auto-Regressive Integrated Moving Average (ARIMA) family. As reviewed by Van Arem et al. (1997), these models hypothesize that traffic flow evolves as a linear stationary process. Williams (1999) advanced this domain by introducing Seasonal ARIMA (SARIMA), which applies seasonal differencing to address the inherent weekly periodicity of traffic data (Wold decomposition). Due to their rigorous statistical foundation, these models became the industry standard for single-point forecasting.

Limitations: The applicability of ARIMA-based models is fundamentally constrained by their linear and stationary assumptions. As noted by Vlahogianni et al. (2004), they fail to capture the highly non-linear dynamics of traffic flow, such as the formation and propagation of shockwaves during congestion. Furthermore, these models typically treat each sensor as an isolated time series, ignoring the spatial topology of the road network and the interactive dependencies between upstream and downstream flows.

### 2.1.2 Physics-Based and State-Space Models

Parallel to statistical methods, researchers have attempted to integrate traffic flow theory into prediction via state-space formulations. A classic approach involves Kalman Filtering (KF), which links unobservable state variables to roadside observations (Whittaker et al., 1997). More sophisticated approaches utilize Dynamic Traffic Assignment (DTA) logic to estimate Origin-Destination (OD) flows and simulate driver behavior under control strategies. These methods explicitly incorporate physical relationships (e.g., the fundamental diagram) between speed, flow, and density.

Limitations: While offering high interpretability, these models suffer from the "Calibration Dilemma." They rely heavily on idealized boundary conditions and hard-to-obtain inputs (e.g., real-time dynamic OD matrices). As highlighted in classic studies, while physics-based updates improve accuracy during incidents, the complexity of calibrating global network dynamics in real-time restricts their scalability and robustness in noisy urban environments.

### 2.1.3 Early Non-Parametric and Pattern-Based Methods

To overcome the rigidity of parametric assumptions, non-parametric approaches were developed to "let the data speak." k-Nearest Neighbors (k-NN) regression, pioneered by Smith et al. (2002), predicts future states by searching for analogous historical patterns based on feature distance. These methods demonstrated that simple pattern recognition could outperform naive forecasts in short horizons by adapting to recurrent events. Early shallow Neural Networks also emerged during this period as universal non-linear regressors.

Limitations: Despite their flexibility, these methods face the "Curse of Dimensionality" when applied to large-scale networks. Crucially, algorithms like k-NN rely on statistical similarity in feature space rather than physical connectivity in topological space, making them unable to explicitly model the spatiotemporal propagation of traffic states (e.g., how a bottleneck propagates upstream).

## 2.2 Modern Deep Learning and Graph-Based Approaches

In recent years, the paradigm of traffic forecasting has shifted from statistical methods to Deep Learning (DL), with Graph Neural Networks (GNNs) emerging as the dominant framework. Unlike traditional Convolutional Neural Networks (CNNs) restricted to Euclidean grids, GNNs are designed to process non-Euclidean topologies, making them theoretically suitable for complex road networks.

### 2.2.1 Spatial Dependency Modeling

The foundational breakthrough lies in redefining the convolution operation on graphs to capture spatial correlations. Kipf & Welling (2017) proposed the Graph Convolutional Network (GCN), which approximates spectral convolution via first-order Chebyshev polynomials, allowing efficient feature aggregation from local neighbors. To address the limitations of static weights, Veličković et al. (2018) introduced Graph Attention Networks (GAT), employing self-attention mechanisms to dynamically assign importance weights to different neighbors. While these methods excel at capturing static spatial correlations, they inherently treat traffic nodes as abstract vertices, often overlooking the anisotropic nature of traffic flow (i.e., the distinct influence of upstream inflow versus downstream congestion).

### 2.2.2 Spatiotemporal Fusion Frameworks

Since traffic flow is inherently dynamic, pure spatial GNNs are typically integrated with temporal sequence modules. A seminal work is the Diffusion Convolutional Recurrent Neural Network (DCRNN) (Li et al., 2018), which models traffic as a diffusion process on a directed graph. By integrating diffusion convolution into the GRU gating mechanism, DCRNN captures the stochastic nature of traffic states. Subsequently, Wu et al. (2019) developed Graph WaveNet, combining graph convolutions with dilated causal convolutions to expand the receptive field exponentially. This architecture captures long-range temporal dependencies without the sequential computation bottleneck of RNNs. These "ST-GNN" frameworks currently represent the state-of-the-art in prediction accuracy.

### 2.2.3 Dynamic Structure Learning

Recognizing that the pre-defined physical topology may not fully reflect dynamic traffic correlations (e.g., ghost jams or hidden dependencies), recent research focuses on Structure Learning. Dynamic Graph Neural Networks (Bai et al., 2020; Chen et al., 2020) employ adaptive mechanisms to evolve the adjacency matrix at each time step. Multi-view GNNs (Lv et al., 2020) further fuse heterogeneous graphs—such as physical connectivity, POI similarity, and traffic pattern proximity—to learn latent spatial dependencies beyond simple road connections.

### 2.2.4 Critical Limitations: The "Black-Box" Barrier

Despite their superior performance on benchmark datasets, these deep learning models face critical challenges that hinder their deployment in safety-critical engineering systems:

**The Interpretability and Causality Deficit:** Complex architectures like DCRNN or Adaptive GNNs operate as "Black Boxes." They learn implicit weight matrices that minimize statistical error but lack physical correspondence. When a model predicts a congestion peak, it is mathematically opaque whether this result stems from upstream wave propagation or a learned temporal artifact. This lack of transparency is unacceptable for traffic operators who require actionable, causal insights (e.g., "congestion is caused by the bottleneck at node i").

**Physical Inconsistency:** Most GNNs treat traffic flow purely as numerical vectors, ignoring fundamental conservation laws and the flow-density-speed relationship. Consequently, they tend to "over-smooth" predictions, failing to capture sharp shockwaves caused by accidents or sudden capacity drops, as the loss functions (e.g., MSE) favor mean-reversion.

**Computational Scalability:** Models involving dynamic graph learning or multi-head attention scale quadratically with the network size (O(N²)). Calculating and updating a dense adjacency matrix for a city-wide network with thousands of links is computationally prohibitive for real-time applications.

## 2.3 Physics-Informed and Hybrid Approaches

While deep learning excels in pattern matching, it often neglects the conservation laws and causality governing traffic flow. To bridge this gap, recent research has pivoted towards Physics-Informed Machine Learning (PIML), aiming to synergize explicit traffic flow theories with data-driven expressiveness.

### 2.3.1 Classical Traffic Flow Theory: The Foundation

The theoretical bedrock of traffic dynamics is the Lighthill-Whitham-Richards (LWR) model (Lighthill & Whitham, 1955), which conceptualizes traffic as a compressible fluid governed by the continuity equation ( $\frac{\partial q}{\partial x} + \frac{\partial \rho}{\partial t} = 0$ ). To implement this numerically on networks, Daganzo (1994, 1995) proposed the Cell Transmission Model (CTM), a discrete approximation that simulates flow propagation based on the Fundamental Diagram (FD). Higher-order phenomena, such as stop-and-go waves, are captured by models like Aw-Rascle-Zhang (ARZ) (Aw & Rascle, 2000), which introduce momentum equations to resolve theoretical inconsistencies like "negative velocity."

Limitations: Although these models offer perfect physical transparency, they are inherently deterministic and struggle to assimilate the high-frequency stochastic noise present in real-world data. Moreover, calibrating critical parameters (e.g., jam density, shockwave speed) for city-wide networks is an ill-posed inverse problem that is notoriously difficult to solve in real-time.

### 2.3.2 Physics-Guided Learning Frameworks

To combine the interpretability of theory with the adaptability of learning, hybrid frameworks have emerged, generally falling into two categories:

**Physics-Regularized Learning (Soft Constraints):** The dominant paradigm, popularized by Physics-Informed Neural Networks (PINNs) (Raissi et al., 2019), incorporates physical residuals directly into the loss function ( $J=J_{data} +\lambda J_{physics}$ ). For traffic, Huang & Agarwal (2022) applied this to constrain traffic state estimation using the LWR conservation law. This forces the neural network to explore a solution space that is physically plausible, even with sparse data.

**Physics-Augmented Learning (Feature Fusion):** Another stream feeds outputs from theoretical models as augmented features into neural networks. Zhang et al. (2023) utilized simulation data from METANET to guide a DL predictor, while Yao et al. (2023) developed a Physics-Aware Learning (PAL) framework that explicitly calculates shockwave velocities to correct LSTM predictions, significantly reducing spatial errors in congested scenarios.

### 2.3.3 The Remaining Gap: From Constraint to Architecture

Despite these advances, a critical methodological gap remains for large-scale network prediction:

**"Black Box with Handcuffs":** Most PIML methods use physics merely as a soft constraint (Loss) or an external feature. The core predictor remains a neural network (Black Box). While the output is regularized, the internal inference process (matrix weights) remains uninterpretable. It is still difficult to trace how a specific upstream perturbation propagates to a downstream node within the network layers.

**Computational Scalability:** Embedding Partial Differential Equations (PDEs) or iterative numerical solvers (like CTM) within the training loop of a neural network entails a heavy computational burden. Solving high-dimensional derivatives for thousands of road links is often prohibitive for real-time online applications.

**Lack of Network-Wide Propagation Logic:** Existing PIML methods predominantly focus on single-link or corridor-level dynamics (e.g., estimating density on a highway segment). There is a scarcity of frameworks that explicitly model network-level propagation—how congestion spills over complex topologies—while retaining the intrinsic transparency of mechanism-based models.

This study aims to fill this gap. Unlike existing PIML methods that apply physics as an external patch, we construct the prediction architecture itself based on the physical propagation mechanism (Spatiotemporal Dispersion). By deriving the transition and impedance kernels directly from data, our model achieves the intrinsic interpretability of physical models and the scalability of data-driven methods.