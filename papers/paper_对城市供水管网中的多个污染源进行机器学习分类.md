# sensors


## 1. Introduction

Contamination in water distribution networks can occur due to deliberate or unin-
tentional intrusions and it is of extreme importance to determine the contamination event
parameters so it can be detected which parts of water distribution networks have been
exposed to the contaminant and needed measures can be conducted. This is considered to
be an inverse problem since injection location, injection starting time, injection duration,
and contaminant chemical concentration value needs to be predicted based on sensor
measurements. Numerical simulations are used to determine these parameters, but model
limitations need to be taken into consideration. EPANET [1] is the most commonly used
software for water distribution network simulations and uses an advective approach which
cannot efﬁciently analyze contaminant dispersion in the networks. Piazza et al. [2] con-
ducted experiments where it was shown that dispersive and diffusive processes must be
incorporated in the transport model for less turbulent ﬂuid ﬂows to achieve more accurate
results than the pure advection model. Also, EPANET assumes complete mixing in all
network junctions, which can be valid only in the case of a single outlet or if there is con-
siderable distance between two junctions. Therefore, EPANET extension EPANET-BAM [3]
was proposed which uses experimentally calibrated mixing model parameter to more
accurately model mixing in network junctions. A number of studies investigated mixing
behavior for different conditions, both experimentally and numerically, to further enhance
these simpler 1D numerical models [4–9].
Sensors 2021, 21, 245. https://doi.org/10.3390/s21010245
https://www.mdpi.com/journal/sensors

Sensors 2021, 21, 245
2 of 15
Huang and McBean [10] investigated a data mining approach for identifying possible
sources of intrusion where single and multiple injection scenarios were considered. In the
case of multiple injection scenario, the method provided a limited number of nodes with
the probability of them being the true contamination source. However, in their work, it is
not predicted what is the true number of injection locations. In Wang and Harrison [11] a
Bayesian approach was coupled with Support Vector Regression to provide a probability
distribution of water network nodes being contaminant sources. However, a single injection
is assumed, and it is noted that multiple contaminant sources should be considered in future
work where the likelihood evaluation needs to be adjusted. Seth et al. [12] investigated
the efﬁciency of three different methods for source detection; Bayesian probability-based
method, backtracking method (using contaminant status algorithm), and optimization-
based method where accuracy in case of multiple injection locations was investigated for
two and three contamination injection locations. It was noted that the Bayesian method is
designed only for a single contamination location while the contaminant status algorithm
used in De Sanctis et a

## 2. Materials and Methods

2.1. Benchmark Water Supply Networks
Prediction of the number of injection sources is conducted for two benchmark different
sized networks. Investigated networks are Net3 EPANET2 example consisting of 92 nodes
and Richmond network consisting of 865 nodes, obtained from The Centre for Water
Systems (CWS) at the University of Exeter [24]. For the Net3 network, two different sensor
layouts are investigated. In ﬁrst layout four sensors were placed in network nodes 117,
143, 181, and 213 as in [25] and in second layout four sensor were placed in network
nodes 115, 119, 187, and 209 as in [26]. Additionally, an investigation of the number of
sensors was conducted. For the ﬁrst layout, two sensors were placed in network nodes
117 and 181, and for the second layout sensors were placed in network nodes 119 and
209. For Richmond network ﬁve sensors were placed in network nodes 93, 352, 428, 600,
and 672 where sensor layout was taken from [27]. Layout with three sensors placed in
network nodes 93, 428, and 672 was also considered. Considered networks with sensor
layouts can be seen in Figures 1 and 2.
Contamination scenarios are simulated using EPANET2 version 2.0.12. where for both
networks, simulation time is 24 h with a hydraulic time step of 10 min, quality time step
5 min, pattern time step 10 min and report time step 1 h. For all conducted simulations,
the EPANET2 ﬂow paced method is used for the contaminant injection. Contamination
scenario parameters are chosen randomly. The number of injection locations is chosen from
1 to 4 nodes. The starting time and duration of contamination injection are chosen from 0
to 24 h. Concentration was randomly chosen from 10 to 2000 mg/L. For contamination
scenarios with multiple injection locations starting time, duration, and concentration was
kept the same for every injection location.
Prior to simulating multiple injection scenario, independent simulations for each
randomly chosen node as a source of contamination are conducted. If contamination is not
registered for the investigated node with chosen contamination parameters, that node is
eliminated as source location and only nodes for which contamination was detected in at
least one sensor are kept as a source of contaminant. For example, if four source nodes are
randomly chosen to be the source of contamination, but only two source nodes inﬂuence
sensor detection of contaminant, the same time series of sensor measurements would be
obtained for two, three, and four injection locations since the latter two do not inﬂuence
contamination measurements. If four sources are given to the prediction model as input,
where contamination can be measured only from two sources, that would signiﬁcantly
reduce the accuracy of the prediction model. Thus, only nodes which contribute to the
contamination measurements in sensors are considered for multiple injection scenario.

Sensors 2021, 21, 245
4 of 15
Figure 1. Net3 network with sensor layouts.
Figure 2. Richmond network det

## 3. Results

3.1. Model Accuracy
The inﬂuence of input data on prediction model accuracy is investigated for both
benchmark networks where data ranged from 50,000 to 500,000 inputs (Figure 6). An inves-
tigation is conducted for prediction model with 2 categories (model predicts only if single
or multiple injection locations are present) and with 4 categories (model predicts an exact
number of injection locations). For each model and each number of inputs, 20 runs were
conducted to take into consideration the inﬂuence of random seed. For the Net3 network
second sensor layout with sensors placed in nodes 115, 119, 187, and 209 was considered.
For Net 3 results are presented for both RF and NN prediction models. Standard deviation
ranged from 0.63% for 50,000 to 0.33% for 500,000 inputs for NN model, and from 0.33%
for 50,000 to 0.1% for 500,000 inputs. It can be observed that the RF model has slightly
better accuracy for all investigated models. Also, due to the faster execution time of the RF
model, for all further analyses, only RF results will be presented. For Richmond network,
standard deviation ranged from 0.28% for 50,000 inputs to 0.12% for 500,000 inputs which
indicates the stability of the model. Presented results are an average of all 20 runs.
(a)
Figure 6. Cont.

Sensors 2021, 21, 245
9 of 15
(b)
Figure 6. Accuracy of prediction models for different number of inputs for (a) Net3 network and
(b) Richmond network.
It can be observed that even for a small number of input data considerable accuracy
can be achieved. For model with 2 categories even with 50,000 inputs accuracy of the model
is above 85% for both considered networks. After 200,000 inputs accuracy of the models
for both networks tend to only slightly increase with the further increase of the number of
input data. For 500,000 inputs accuracy of the Net3 network is 66.83% and for Richmond
network 72.96%. When simpliﬁcation is made, and the model only needs to predict single
or multiple injection locations, accuracy signiﬁcantly increases and for 500,000 inputs for
the Net3 network is 91.46% and for the Richmond network 93.4%.
3.2. Threshold Inﬂuence
To further increase the accuracy of the prediction model, the threshold value is introduced
for the model which predicts 2 categories. Detailed results are presented for models with
500,000 inputs for Net3 (Tables 1 and 2) and Richmond network (Tables 3 and 4). Presented
results are the average of values obtained from 20 runs. As expected, with the increase in
threshold value accuracy of the prediction model increases. However, with a greater threshold
value, a greater number of single injection scenarios, as a precaution, are classified as multiple
sources, thus a smaller number of true single injection scenarios are detected. For both
networks, when the threshold value is 95%, a very low percentage of correct prediction of
single source scenarios can be observed when prediction model parameters chosen with grid
search optimization method (250 es

## 4. Discussion

Accuracy of prediction models for both networks has similar results with small differ-
ences, which shows that the proposed methodology could be successfully applied to other
networks. Further investigation should be conducted for large size water distribution net-
works and different sensor placements, to fully investigate the robustness of the proposed
method. Also, it must be noted that simpliﬁcation was used in this study, where all source
nodes had the same parameters (injection starting time, duration, and concentration value),
thus, it should be investigated how the model predicts if those parameters are different for
each injection node.
Although slightly, with the increase of input data model accuracy still increases, so in
further study a greater number of data inputs should be investigated. Also, in the proposed
scenarios report time step was chosen to be 1 h, resulting in 25 features per sensor. It should
be investigated if a greater number of features, i.e., smaller report time step would increase
model accuracy and if similar model accuracy could be achieved with a smaller number of
contamination readings. The optimal number of features and inputs should be investigated
to achieve great accuracy but with reasonable execution time. However, to obtain a greater
number of inputs a greater amount of time is needed, so the model should be trained
before the actual contamination event occurs. In that case, the model would be trained
with simulation results with average demand patterns. This surely would mean that true
contamination event will have different demands which would inﬂuence the accuracy
of the prediction model. Investigation of demand uncertainty with arbitrarily chosen
demand variation spans showed that small differences of base demands slightly inﬂuence
prediction model accuracy. However, it must be taken into consideration that when base
demand variation is deﬁned with percentage, small demand variation is achieved when
base demand is small and greater demand variation only when base demand is greater.
Greater difference in demands should be further investigated since the usual variability
of consumption can be greater than considered in this paper. Different machine learning
models, with different expected demand patterns, can be prepared for contamination
event so prediction can be obtained instantaneously. However, in case of contamination
event, greater oscillations in the hydraulics of water distribution network could occur, such

Sensors 2021, 21, 245
13 of 15
as pipe burst or some other unplanned event, which would greatly inﬂuence change in
demand patterns. Thus, it would be beneﬁcial to investigate other algorithms that could
increase accuracy with a smaller number of input data. In that case, input data can be
obtained after the contamination event occurred, in a reasonable amount of time. That
would be greatly beneﬁcial since the simulation model can then be calibrated with sensor
measurements from the ﬁeld and i

**Key Findings:**
- Also, it must be noted that simpliﬁcation was used in this study, where all source
nodes had the same parameters (injection starting time, duration, and concentration value),
thus, it should be investigated how the model predicts if those parameters are different for
each injection node.

## 5. Conclusions

In this paper, the machine learning approach is presented which helps identify the
number of injection locations based on sensor measurements. Random Forest classiﬁer and
Neural Network classiﬁer are used on medium-sized benchmark network, where Random
Forest classiﬁer provided better accuracy and faster execution time, thus is used for all
other investigations. Two different sized benchmark networks are considered, where it is
shown that the machine learning approach can be successfully used to predict the number
of injection locations. This can help deﬁne the number of optimization parameters, where
redundant parameters can be avoided which needlessly increase the complexity of the
problem. The prediction model shows great accuracy when it predicts only if single or
multiple injection locations occurred. The threshold value is proposed which further
increases model accuracy since the single injection scenario is assumed only if the model
predicts with certainty greater than the threshold value. Lower accuracy is obtained
when the exact number of injection locations is predicted. The accuracy of the prediction
model is investigated for different sensor layouts and in case of demand uncertainties and
fuzzy sensors. Conducted research showed promising results, where exploration of other
algorithms and increased number of input data should be investigated to further increase
the accuracy of both models.
Author Contributions: Conceptualization, I.L. and L.G.; Data curation, I.L.; Formal analysis, I.L;
Investigation, I.L. and L.G.; Methodology, I.L. and L.G.; Resources, Z. ˇC. and L.K.; Software, I.L.;
Supervision Z. ˇC. and L.K.; Validation, I.L.; Visualization; I.L.; Writing—original draft, I.L.; Writing—

Sensors 2021, 21, 245
14 of 15
review and editing, L.G., Z. ˇC. and L.K. All authors have read and agreed to the published version of
the manuscript.
Funding: This research received no external funding.
Data Availability Statement: The data presented in this study are available on request from the
corresponding author.
Conﬂicts of Interest: The authors declare no conﬂict of interest.
References
1.
Rossman, L.A. EPANET 2: Users Manual. 2000. Available online: https://epanet.es/wp-content/uploads/2012/10/EPANET_
User_Guide.pdf (accessed on 6 September 2020).
2.
Piazza, S.; Blokker, E.M.; Freni, G.; Puleo, V.; Sambito, M. Impact of diffusion and dispersion of contaminants in water distribution
networks modelling and monitoring. Water Supply 2020, 20, 46–58. [CrossRef]
3.
Ho, C.K.; O’Rear, L., Jr. Evaluation of solute mixing in water distribution pipe junctions. J. Am. Water Work. Assoc. 2009,
101, 116–127. [CrossRef]
4.
Yu, T.; Tao, L.; Shao, Y.; Zhang, T. Experimental study of solute mixing at double-Tee junctions in water distribution systems.
Water Sci. Technol. Water Supply 2015, 15, 474–482. [CrossRef]
5.
Yu, T.; Qiu, H.; Yang, J.; Shao, Y.; Tao, L. Mixing at double-Tee junctions with unequal pipe sizes in water distribution systems.
Water Sci.

**Key Findings:**
- Data Availability Statement: The data presented in this study are available on request from the
corresponding author.
