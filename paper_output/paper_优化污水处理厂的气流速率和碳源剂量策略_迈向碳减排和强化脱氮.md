# Optimizing airflow rate and carbon source dosage strategies for wastewater


## 1. Introduction

1.1. Background
WWTPs play a pivotal role in sustainable city development by 
ensuring safe wastewater treatment and discharge and reducing envi­
ronmental pollution with lower carbon emission. To meet increasingly 
stringent effluent quality standards, key operational variables such as 
airflow rate, reflux ratio, and carbon source dosage are adjusted based 
on pre-defined strategies [1]. Traditionally, wastewater treatment is 
viewed as a process that trades energy for water quality [2] which 
indicating that a higher pollutant removal rate is associated with 
increased treatment costs and greater GHG emissions in generally. With 
the growing focus on GHG emissions and sustainable development, 
attention has shifted toward a tri-objective optimization problem 
encompassing water quality, treatment costs, and carbon emissions. 
Effluent quality, especially TNeff, is a major contributor to direct carbon 
emissions [3–5].Traditional operation strategies rely heavily on manual 
experience [6], leading to inefficiencies and high energy consumption. 
Therefore, developing low-carbon, dynamic, and stable operational 
strategies is critical for advancing sustainable and cleaner wastewater 
treatment processes. Despite this need, research in WWTP operation 
strategies faces several challenges at present, including difficulties in 
monitoring gas emissions [7], the dynamic and nonlinear nature of the 
treatment process [8], and the time-lag characteristics of operational 
adjustments [9].
1.2. Research of low-carbon operation strategies
Aeration and external carbon dosage systems are the key contribu­
tors to energy consumption and GHG emissions. Hence, recent re­
searches on low-carbon operational strategies focus prominently on 
these systems [10]. The aeration system is specifically designed to 
support the growth of microorganisms involved in various biochemical 
reactions, including nitrification, anaerobic ammonium oxidation and 
denitrification [11,12]. Low-carbon strategies for aeration systems 
include two aspects, one is to provide an exact airflow rate equal to the 
* Corresponding author.
E-mail addresses: lixuefei@qut.edu.cn (X. Li), smiao@qut.edu.cn (S. Miao), liuchangqing@qut.edu.cn (C. Liu). 
Contents lists available at ScienceDirect
Journal of Water Process Engineering
journal homepage: www.elsevier.com/locate/jwpe
https://doi.org/10.1016/j.jwpe.2025.107513
Received 11 December 2024; Received in revised form 11 March 2025; Accepted 15 March 2025  
Journal of Water Process Engineering 72 (2025) 107513 
Available online 19 March 2025 
2214-7144/© 2025 Elsevier Ltd. All rights are reserved, including those for text and data mining, AI training, and similar technologies. 

oxygen requirement [13], and the other is dynamic DO control [14]. The 
total oxygen requirement can be calculated based on the oxygen re­
quirements for BOD and nitrate removal [15,16], enabling precise air 
supply management and effectively reducing energy waste [17]. Ad

## 2. Material and methods

As illustrated in Fig. 1, this study aims to propose low-carbon and 
dynamic operation strategies for WWTPs that not only reduce TNeff but 
also reduce carbon emission intensity. Firstly, strategies based on the 
carbon‑nitrogen ratio and gas-water ratio are developed, with specific 
values determined from real-time monitoring data of example WWTP. 
Additionally, both indirect and direct carbon emission intensities are 
introduced for a more comprehensive evaluation. Finally, the GRU- 
LSTM prediction model functions as a trial-and-error tool, accurately 
predicting TNeff, offering decision support for strategies formulation, 
and providing direct emission data for carbon intensity calculations.
2.1. Preliminary analysis
The preliminary analysis is outlined as follows: it explains the 
rationale for selecting TNeff as the research focus, and the reasoning 
behind choosing airflow rate and external carbon source dosage as the 
manipulated variables.
Firstly, approximately half of China WWTPs are facing significant 
challenges in nitrogen removal [43]. According to monitoring data of 
example WWTP, 31 data points exceed 80 % of the TNeff standard value 
(15 mg/L), indicating a high-risk level. Additionally, a previous study 
indicated that the removal of 1 kg of nitrogen typically requires 
approximately 1.50–2.26 kWh of electricity. Improving nitrogen 
removal is an energy-intensive process that leads to increased GHG 
emissions. As a result, TNeff has been identified as the focal point of this 
research due to its critical role in both effluent quality and sustainable 
development goals.
The aeration system and carbon source dosage are the primary 
energy-consuming units, contributing significantly to carbon emission. 
In practice, WWTP operators typically adjust the airflow rate via air 
compressors, making the airflow rate a key manipulated variable in 
operations, rather than DO. Additionally, maintaining a suitable car­
bon‑nitrogen ratio, which varies depending on water quality, is essential 
for efficient nitrogen removal. External carbon sources play a crucial 
role in achieving this balance. Furthermore, the relationship between 
carbon source dosage and airflow rate is highly interactive: increasing 
carbon dosage requires higher airflow to manage the excess carbon load. 
Consequently, the airflow rate and external carbon source dosage are 
identified as the primary variables in this study.
2.2. Wastewater treatment process
Example WWTP, is situated in Shandong province, within the 
northern temperate zone of China. The designed treatment capacity is 
up to 25,000 m3 per day, with influent comprising domestic and in­
dustrial wastewater that complies with discharge standards for pipeline 
systems (Table S1). The treatment process includes the primary treat­
ment process, biochemical process utilizing Anaerobic-Anoxic-Oxic 
activated sludge for nitrogen and phosphorus removal, and the 
advanced treatment process. The treatment process and

**Key Findings:**
- 1, this study aims to propose low-carbon and 
dynamic operation strategies for WWTPs that not only reduce TNeff but 
also reduce carbon emission intensity.
- Firstly, approximately half of China WWTPs are facing significant 
challenges in nitrogen removal [43].
- The aeration system and carbon source dosage are the primary 
energy-consuming units, contributing significantly to carbon emission.

## 4. Conclusion

This study proposes an integrative framework for optimizing dy­
namic, low-carbon operation strategies of WWTPs, supported by a case 
study, the key findings are summered as follows:
(1) The established GRU-LSTM prediction model has been trained 
and validated based on one year of hourly monitoring data in example 
WWTP. Results demonstrated that the model accurately predicted 
effluent TN concentrations under various influent conditions and oper­
ational parameters, making it an effective evaluation tool for nitrogen 
removal performance.
(2) The case study showed a significant decrease in effluent TN 
concentrations and improved stability when applying strategies that 
maintained a carbon‑nitrogen ratio below 4 and a gas-water ratio below 
6. While a clear trade-off between effluent TN concentration and carbon 
emission intensity was identified. Moreover, the cumulative effect of 
prolonged low airflow rate and insufficient dosing led to rising TN 
concentrations over time.
(3) In the case study, the proposed strategies effectively reduced 
indirect carbon emission intensity while enhancing nitrogen removal. 
Results showed that ICEI decreased by an average of 4.18 % under the 
proposed strategies, with effluent TN concentrations decreasing by an 
average of 1.71 mg/L and fluctuations reducing from 1.32 mg/L to 0.98 
mg/L.
CRediT authorship contribution statement
Xuefei Li: Writing – original draft, Visualization, Methodology. 
Huaying Sun: Validation, Software, Data curation. Zuoqian Hu: 
Methodology, Data curation. Sheng Miao: Writing – review & editing, 
Resources, Data curation, Conceptualization. Changqing Liu: Writing – 
review & editing, Supervision.
Declaration of competing interest
The authors declare that there is no conflict of interest regarding the 
publication of this paper.
Acknowledgments
This work received support from the National Key Research and 
Development Program of China (NO.2020YFD1100303). We extend our 
gratitude to Rizhao City Investment Group Co., Ltd. for their assistance 
in data collection from the example WWTP.
Appendix A. Supplementary data
Supplementary data to this article can be found online at https://doi. 
org/10.1016/j.jwpe.2025.107513.
Data availability
Data will be made available on request.
References
[1] Z. Wang, X. Zhou, H. Wang, Z. Huang, J. Ji, Z. Peng, et al., XGB-SEGA coupled 
energy saving method for wastewater treatment plants, Appl Water Sci 2 (14) 
(2024) 13–29.
[2] H. Wang, Y. Wang, X. Wang, W. Yin, T. Yu, C. Xue, et al., Multimodal machine 
learning guides low carbon aeration strategies in urban wastewater treatment, 
Engineering 36 (2024) 51–62.
[3] A. Ramaswami, K. Tong, A. Fang, R.M. Lal, A.S. Nagpure, Y. Li, et al., Urban cross- 
sector actions for carbon mitigation with local health co-benefits in China, Nat. 
Clim. Chang. 10 (7) (2017) 736–742.
[4] X. Liang, S. Zhang, Y. Wu, J. Xing, X. He, K.M. Zhang, et al., Air quality and health 
benefits from fleet electrification in China, Natur

**Key Findings:**
- This study proposes an integrative framework for optimizing dy­
namic, low-carbon operation strategies of WWTPs, supported by a case 
study, the key findings are summered as follows:
(1) The established GRU-LSTM prediction model has been trained 
and validated based on one year of hourly monitoring data in example 
WWTP.
- (2) The case study showed a significant decrease in effluent TN 
concentrations and improved stability when applying strategies that 
maintained a carbon‑nitrogen ratio below 4 and a gas-water ratio below 
6.
- Results showed that ICEI decreased by an average of 4.18 % under the 
proposed strategies, with effluent TN concentrations decreasing by an 
average of 1.71 mg/L and fluctuations reducing from 1.32 mg/L to 0.98 
mg/L.
