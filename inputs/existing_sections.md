**Research on Target Detection Technology of Power Equipment Nameplates
Based on Deep Learning**

**ABSTRACT**

The power system is an important basic guarantee for the normal
operation of modern society, and all kinds of large, medium and small
power equipment are an important part of the power system. With the
continuous development of the power industry, the number and types of
power equipment are increasing day by day, and the management and
maintenance of equipment have become more and more important. The
nameplate of power equipment usually contains the key parameters and
information of the equipment, such as model, rated voltage, rated power,
etc. Accurate access to brand name information is of great significance
for the operation management and maintenance of equipment. However, in
the operation and maintenance process of many larger power equipment,
the nameplate will be smaller relative to the equipment body due to the
cost and technical constraints such as the power equipment nameplate,
and there is the positioning problem that the power equipment nameplate
background is complex, and the nameplate target is small in this
process, and the efficiency of relying on manual recognition is low, and
the nameplate picture extracted by manual mode has the wrong picture and
will bring difficulties to the subsequent text recognition work. In
addition, due to the fact that the definition of the existing shooting
equipment may be not high and the shaking that is difficult to avoid in
the shooting process, after correctly locating the position of the
nameplate of the power equipment in the image, solving the problem of
misrecognition and misrecognition of the subsequent text recognition
model and even the inability to read manually due to the low definition
of the picture is also the key difficulty of extracting the nameplate
information of the power equipment.

In order to solve the problem of text recognition caused by insufficient
detection accuracy and blurred image of nameplate small target in the
operation and maintenance scenario of power equipment, a collaborative
solution of object detection and super-resolution image processing based
on deep learning was proposed. Firstly, the scheme constructs a
nameplate dataset of power equipment including multi-condition
simulation, and uses YOLO（You Only Look Once） series algorithms
（YOLOv8, YOLOv10, YOLOv11） to train the small target detection model,
and it is found that YOLOv11 has the best comprehensive performance in
terms of detection accuracy, inference speed and model size through
comparative experiments. Furthermore, the Real-ESRGAN model based on
adversarial network is introduced, and the resolution of the detected
nameplate area is enhanced through the non-blind super-resolution
training strategy, and the reconstruction effect of PSNR=28.86dB and
SSIM=0.8138 is realized on the self-built dataset, which significantly
improves the sharpness of text edges. Finally, a front-end and back-end
separation system based on Flask+Vue is designed and implemented, which
integrates object detection and super-resolution image processing
functions, and supports multi-model deployment and visual interaction.
Experimental results show that the scheme can effectively detect the
nameplate target of power equipment, and can make the text part
significantly clear, so as to effectively reduce the probability of
misrecognition in text recognition work, and provide a basis for the
intelligent operation and maintenance of power equipment.

**Key words：**Power equipment nameplate, Small-target
detection,Super-resolution reconstruction, YOLOv11,Real-ESRGAN,Front-end
and back-end separation

目 录

[1 引 言 [1](#引-言)](#引-言)

[1.1 课题背景 [1](#课题背景)](#课题背景)

[1.2 国内外研究现状 [2](#_Toc198729267)](#_Toc198729267)

[1.2.1 目标检测技术国内外研究现状
[2](#目标检测技术国内外研究现状)](#目标检测技术国内外研究现状)

[1.2.1 图像清晰化技术国内外研究现状
[5](#图像清晰化技术国内外研究现状)](#图像清晰化技术国内外研究现状)

[1.4 本文研究目标及内容 [8](#本文研究目标及内容)](#本文研究目标及内容)

[![](C:\Users\Administrator\Desktop\2425_31_10247_080601_2153413_CL\media_zhao/media/image2.wmf)2
基于YOLO系列算法的电力设备铭牌目标检测模型 9](#_Toc261510875)

[2.1 卷积神经网络 [9](#卷积神经网络)](#卷积神经网络)

[2.1.1 CNN基本架构 [9](#_Toc198729273)](#_Toc198729273)

[2.2 基于深度学习的YOLO系列目标检测模型
[12](#基于深度学习的yolo系列目标检测模型)](#基于深度学习的yolo系列目标检测模型)

[2.2.1 基于Ultralytics库的YOLO系列算法介绍
[12](#_Toc198729275)](#_Toc198729275)

[2.2.2 电力设备铭牌定位数据集预处理
[16](#_Toc198729276)](#_Toc198729276)

[2.2.3 YOLOv8、YOLOv10与YOLOv11模型性能对比实验
[20](#_Toc198729277)](#_Toc198729277)

[2.3 本章小结 [23](#本章小结)](#本章小结)

[3 基于对抗网络的Real-ESRGAN超分辨图像处理模型
[24](#基于对抗网络的real-esrgan超分辨图像处理模型)](#基于对抗网络的real-esrgan超分辨图像处理模型)

[3.1 超分辨图像处理网络结构
[24](#超分辨图像处理网络结构)](#超分辨图像处理网络结构)

[3.1.1 传统网络模型 [24](#传统网络模型)](#传统网络模型)

[3.1.2 生成对抗网络模型 [25](#生成对抗网络模型)](#生成对抗网络模型)

[3.2 基于对抗网络的Real-ESRGAN超分辨图像处理网络模型
[26](#基于对抗网络的real-esrgan超分辨图像处理网络模型)](#基于对抗网络的real-esrgan超分辨图像处理网络模型)

[3.2.1电力设备铭牌超分辨图像处理数据集
[28](#电力设备铭牌超分辨图像处理数据集)](#电力设备铭牌超分辨图像处理数据集)

[3.2.2基于Real-ESRGAN的电力设备铭牌超分辨图像处理训练
[30](#基于real-esrgan的电力设备铭牌超分辨图像处理训练)](#基于real-esrgan的电力设备铭牌超分辨图像处理训练)

[3.3 本章小结 [32](#本章小结-1)](#本章小结-1)

[4 基于Flask+vue前后端分离的目标检测-超分辨系统
[33](#基于flaskvue前后端分离的目标检测-超分辨系统)](#基于flaskvue前后端分离的目标检测-超分辨系统)

[4.1 系统架构设计 [33](#系统架构设计)](#系统架构设计)

[4.1.1前后端的实现模式 [33](#前后端的实现模式)](#前后端的实现模式)

[4.1.2 Flask+vue框架介绍与部署
[33](#flaskvue框架介绍与部署)](#flaskvue框架介绍与部署)

[4.2 系统功能实现 [34](#系统功能实现)](#系统功能实现)

[4.3 本章小结 [40](#本章小结-2)](#本章小结-2)

[5 结论和展望 [42](#结论和展望)](#结论和展望)

[5.1 总结 [42](#总结)](#总结)

[5.2 展望 [43](#展望)](#展望)

[参考文献 [44](#参考文献)](#参考文献)

[谢辞 [47](#谢辞)](#谢辞)

# 1 引 言

## 1.1 课题背景

电力系统是现代社会正常运行的重要基础保障，各类大中小型电力设备更是电力系统中重要的组成部分。随着电力行业的不断发展，电力设备的数量和种类日益增加，设备的管理和维护变得愈加重要。电力设备铭牌上通常包含了设备的关键参数和信息，如型号、额定电压、额定功率等。这些信息对于设备的运行管理和维护保养都具有重要意义[<sup>\[1\]</sup>](#_Ref198826656)。在许多电力系统运维场景中，比如柴油发电机组运维管理、变电站运维管理和电网状态评估运维工作等，运维人员需要对发电机、变压器、杆塔等多种电力设备进行普查。为确保设备信息的精确性和完整性，运维规程明确要求采集设备整体外观及其铭牌的照片资料，这些资料能准确反映设备的种类、型号、容量和生产厂家等基本信息，这种详细明确的数据记录方法不仅有助于提升电力设备资产管理效率，还能为后续的维护计划制定提供科学依据[<sup>\[2\]</sup>](#_Ref198640245)。

然而，在电力设备运维过程中，运维人员通过拍摄获取的小型电力设备铭牌图片往往方便查看，目标检测与文本信息提取工作相对简单精准，但是在许多较大型的电力设备的运维过程中，电力设备铭牌的成本和技术等限制原因会使铭牌相对设备本体较小，另外，由于现有拍摄设备可能存在的清晰度不高以及拍摄过程中难以避免的抖动的原因，如图1.1所示。这就导致了在采集的电力设备图片上无法通过文本识别模型完成电力设备铭牌信息的提取，大大增加了人工成本。比如在变压器运维过程中，采集到的设备图片中铭牌大小远远小于设备大小，如果再次单独摄取变压器铭牌图片以留存电力设备信息将会带来冗余的人工操作以及不必要的内存占用，通过人工识别可以精准定位图像中较小铭牌的位置，方便后续文本识别工作进行。然而，这一过程中存在着电力设备铭牌背景复杂、铭牌目标小的定位难题，并且人工识别效率低下，如果提取出的铭牌图片存在错误图片将对后续文本识别工作带来困难。其次，在正确定位图片后，解决图片清晰度低导致后续文本识别模型错识误识乃至人工无法阅读的问题也是提取电力设备铭牌信息的关键难点。

因此，本文拟深入研究电力设备铭牌的定位技术以获取最优技术手段来提升铭牌定位精度，而后研究图像的清晰化手段以提升检测目标图像清晰度，从而减少复杂噪音对文本提取工作的影响，从而为电力设备的运维工作提供基础。

<img
src="C:\Users\Administrator\Desktop\2425_31_10247_080601_2153413_CL\media_zhao/media/image4.png"
style="width:4.12in;height:1.74027in" />

图1.1 电力设备铭牌图片采集不利于信息提取的情况

（a）电力设备铭牌目标小 （b）拍摄清晰度不高

## [<span id="_Toc198729267" class="anchor"></span>1.2](#生成函数法及其优势) 国内外研究现状

针对电力设备图片铭牌的定位和图像清晰化问题，其内容主要是定位图像中某一目标的位置和对图像进行清晰化处理，国内外学者对此做了很多研究，主要研究内容集中在目标检测技术和图像清晰化技术。


# 5 结论和展望

## 5.1 总结

本文迎合了电力设备运维智能化、去人工化的工业需求。首先分析了当前电力设备运维过程中快速精准提取铭牌文本信息的重要性，针对铭牌小目标检测精度不足及图像模糊的问题，提出以精准定位铭牌和清晰化铭牌文本部分为研究目标。结合目前在图像处理领域应用广泛的卷积神经网络，通过构建基于YOLO模型和Real-ESRGAN模型的“数据增强-模型优选-系统集成”完整技术链条，有效实现电力设备铭牌部分的精准定位和超分辨重构处理，为实现电力设备铭牌信息的自动化精准提取打下基础。本文主要内容如下：

（1）该研究率先构建了电力设备铭牌数据集，其囊括了多种设备、多种材质以及多种色彩，通过采集超过1500张开源原始图像，并实施精细化的预处理，最终形成了高质量的数据集，此数据集适用于小目标检测与超分辨训练，在数据增强环节，借助OpenCV实现了一系列操作，包括添加高斯噪声、生成不规则遮挡块以及应用动态模糊核等，以此模拟反光、遮挡以及铭牌生锈等复杂工况。结合自定义的数据增强策略，将数据集规模扩充至7000余张，其中小目标样本的占比得到了明显提升，训练集、验证集和测试集按照7:2:1的比例进行划分，借助Python脚本实现了从VOC格式到YOLO所需TXT格式的自动化转换，保证了标签文件与图像的精确对应，为后续模型训练奠定了标准化的数据基础。另外凭借对高清晰度的原始电力设备铭牌图像进行固定下采样处理，构造了Real-ESRGAN模型的数据集，共计800对，该数据集中低质量图像与高质量图像严格对应。

（2）其次通过对比实验优选目标检测模型，基于Ultralytics库对YOLO系列模型的对比实验表明，YOLOv11通过C3K2
模块与PSA 点式空间注意力机制的创新组合，在小目标检测性能上显著优于
YOLOv8 和 YOLOv10。具体而言，C3K2
模块通过空洞卷积重参数化技术，将多分支结构合并为高效的大核卷积，在减少计算量的同时扩大感受野；PSA
注意力机制则通过多头注意力与前馈神经网络，增强对小目标特征的选择性提取能力。实验数据显示，YOLOv11
在自建数据集上mAP值与YOLOv8相差极小，几乎可以忽略，但是在检测速度、模型大小和运算量方面显著小于YOLOv8，在检测精度、轻量化与实时性之间实现了最优平衡。者表明YOLOv11尤其适用于电力设备运维过程中铭牌尺寸小、背景复杂的场景。

（3）进一步针对检测后铭牌图像的模糊问题，研究引入Real-ESRGAN模型并采用非盲超分训练策略，通过构建800对低质-高质图像对来模拟固定下采样退化过程。生成器采用23层
RRDB
残差密集块结构，生成器采用23层RRDB残差密集块结构，借助跨层连接提高特征复用能力，判别器基于U-Net架构并引入光谱归一化，以此提升对图像结构细节的辨别能力。损失函数采用L1损失、VGG感知损失和Relativistic
GAN损失加权的组合，能保证像素级重建精度，又能借助对抗训练提升视觉真实性，实验结果说明，模型在验证集上达到PSNR=28.86dB、SSIM=0.8138，改善了文本识别的输入质量，解决了低分辨率图像致使文本检测模型误识的问题。

（4）最后研究设计并开发了集目标检测与超分辨图像处理功能于一体的前后端系统，后端基于Flask构建RESTful
API，通过 Flask-CORS 解决跨域问题；前端采用 Vue 3+Element Plus
框架，设计了图像或者数据集上传、参数配置（置信度阈值、超分辨图像处理倍数、训练参数配置等）、结果可视化等模块。系统实现了目标检测-超分辨处理的图片推理功能、YOLO训练功能和Real-ESRGAN训练功能，最终结果展示在前端界面，并保存在后台根目录中。

## 5.2 展望

随着深度学习图像处理技术的快速发展，未来研究可围绕模型性能优化、技术部署拓展及行业应用深化三个核心方向展开，推动相关技术在复杂场景下的实用化与规模化应用。

（1）在 YOLO
目标检测模型改进方面，我后续将持续阅读模型改进方面的参考文献，考虑引入多尺度混合注意力机制以增强小目标特征聚焦能力，同时探索元学习驱动的小样本适配算法，解决新型设备铭牌数据稀缺问题；通过神经架构搜索与模型剪枝技术，进一步压缩模型体积至10MB以下并提升边缘设备推理速度，结合跨域迁移学习扩展至电力设备缺陷检测等场景，提升模型泛化能力。

（2）超分辨率重建领域里，文字区域的结构一致性以及退化场景多样性问题是需要着重去解决，一方面，可以试着把Transformer架构引入到生成器设计当中，借助自注意力机制来捕捉文字区域的全局上下文关系，设计文本感知损失函数，借助约束字符间距、笔画连贯性等语义特征，提升生成图像的可读性。另一方面，要扩展真实退化模型的多样性，构建涉及模糊、噪声、低分辨率等多种退化模式的盲超分数据集，以此提高模型对未知退化场景的鲁棒性，阅读文献时，还了解到一种基于关联文字的超分辨图像处理模型，也就是借助学习低分辨率图像里的特征，映射到对应的文字实现低分辨率图像中文字的精准提取。

（3）在工程落地这一环节，要促使目标检测技术和超分辨图像重建技术实现集成以及协同发展，比如把优化后的模型部署到边缘计算设备上，借助NPU加速达成在无人机巡检场景下的端侧实时处理，在行业应用领域，要推进技术标准化以及服务化进程，借助API接口给中小企业提供云端服务，降低技术方面的门槛，帮助电力设备运维朝着智能化方向升级。另外还得留意复杂工业环境下存在的鲁棒性挑战，例如凭借跨学科融合以及硬件适配优化，提高系统在高温、高湿、强震动等极端条件下的稳定性和实用性。



**Research on Text Detection and Recognition Technology for Power
Equipment Nameplates**

**ABSTRACT**

With the rapid development of the power industry, the quantity and types
of power equipment have increased dramatically. As a crucial carrier of
key equipment information, the accurate and efficient detection and
recognition of text information on power equipment nameplates are vital
for equipment operation and maintenance management as well as future
recycling. Against the backdrop of the rapid advancement of deep
learning and computer vision technologies, traditional methods for
acquiring information from power equipment nameplates can no longer meet
industry demands. Existing related research has shortcomings in handling
complex background interference, small text, and dense parameter
recognition, making it difficult to balance high precision and low
resource consumption. Therefore, this paper intends to conduct research
on text detection and recognition technologies for power equipment
nameplates. By constructing a dedicated dataset, optimizing deep
learning models, and developing a recognition system, the goal is to
achieve high-precision and low-resource-consumption nameplate text
detection and recognition, thereby providing technical support for the
intelligent operation and maintenance management of power equipment.

This paper focuses on the research of text detection and recognition for
power equipment nameplates. Firstly, natural scene images were collected
through independent photography in real environments such as
laboratories and industrial plants, as well as through online
collection. After image compression and size adjustment, the
Doubao-vision-pro-32k large model from Volcano Engine was used to
automatically extract tabular text from power equipment nameplates. The
tabular text was converted into a suitable format and manually reviewed
to form a structured annotated dataset of power equipment nameplates
containing 850 natural scene images. Secondly, based on the General OCR
Theory (GOT-OCR 2.0) model, a nameplate text detection and recognition
model (EPN-GOT-OCR) was built on the constructed power nameplate
dataset, and the model's adaptability to the specific task of nameplate
detection was improved through full-parameter fine-tuning. To reduce the
model's parameter count for edge deployment, Singular Value
Decomposition (SVD) was introduced to decompose the attention parameter
matrix of the model for optimization. The final experimental results
show that the fine-tuned model's performance was significantly improved,
with an F1 score reaching 83.39%, an accuracy of 79.30%, and a recall
rate of 89.65%. After introducing SVD low-rank decomposition, when the
loss threshold was set to 0.3, the model's F1 score, accuracy, and
recall rate all remained above 70%, while the floating-point operation
count decreased by 5.1% and the number of parameters decreased by 6.9%.
In addition, based on the constructed EPN-GOT-OCR model and the VUE
framework, a nameplate detection and recognition system was designed and
implemented to achieve fast and accurate recognition of power
nameplates. The system covers functions such as model selection, image
upload, recognition, and result rendering.

The research achievements of this paper provide a powerful technical
support for the efficient collection and processing of power equipment
nameplate information, and are of great significance for improving the
intelligent level of power equipment management and promoting the
digital and intelligent development of the power industry.

**Key words：**Power Equipment Nameplate, Text Detection and
Recognition, GOT-OCR 2.0 Model, SVD Low-Rank Decomposition

目 录

[1 引 言 [1](#引-言)](#引-言)

> [1.1 课题背景与意义 [1](#课题背景与意义)](#课题背景与意义)
>
> [1.2 铭牌文字信息国内外研究现状
> [2](#铭牌文字信息国内外研究现状)](#铭牌文字信息国内外研究现状)
>
> [1.2.1 文本检测 [2](#文本检测)](#文本检测)
>
> [1.2.2 文字识别 [3](#文字识别)](#文字识别)
>
> [1.2.3 传统的端到端文本检测与识别算法
> [4](#传统的端到端文本检测与识别算法)](#传统的端到端文本检测与识别算法)
>
> [1.2.4 多模态语言模型 [5](#多模态语言模型)](#多模态语言模型)
>
> [1.3 本文研究目标及内容 [7](#本文研究目标及内容)](#本文研究目标及内容)

[2 Transformer理论与铭牌识别结果评估方法
[9](#transformer理论与铭牌识别结果评估方法)](#transformer理论与铭牌识别结果评估方法)

> [2.1 Transformer原理 [9](#transformer原理)](#transformer原理)
>
> [2.1.1 注意力机制 [9](#注意力机制)](#注意力机制)
>
> [2.1.2 编码器和解码器 [11](#编码器和解码器)](#编码器和解码器)
>
> [2.2 评价指标 [12](#评价指标)](#评价指标)
>
> [2.2.1 平均编辑距离 [13](#平均编辑距离)](#平均编辑距离)
>
> [2.2.2 文本检测与识别算法的性能评价指标
> [13](#文本检测与识别算法的性能评价指标)](#文本检测与识别算法的性能评价指标)
>
> [2.2.3 参数量 [14](#参数量)](#参数量)
>
> [2.2.4 计算量 [15](#计算量)](#计算量)
>
> [2.3 本章小结 [15](#本章小结)](#本章小结)

[3 基于GOT-OCR 2.0的铭牌文本检测与识别模型及优化
[17](#基于got-ocr-2.0的铭牌文本检测与识别模型及优化)](#基于got-ocr-2.0的铭牌文本检测与识别模型及优化)

> [3.1 电力设备铭牌数据集构建
> [17](#电力设备铭牌数据集构建)](#电力设备铭牌数据集构建)
>
> [3.1.1 数据集概况 [17](#数据集概况)](#数据集概况)
>
> [3.1.2 数据采集策略 [17](#数据采集策略)](#数据采集策略)
>
> [3.1.3 数据集预处理及划分方案
> [18](#数据集预处理及划分方案)](#数据集预处理及划分方案)
>
> [3.1.4 数据集标注 [18](#数据集标注)](#数据集标注)
>
> [3.2 基于GOT-OCR 2.0的铭牌文本检测与识别模型
> [19](#基于got-ocr-2.0的铭牌文本检测与识别模型)](#基于got-ocr-2.0的铭牌文本检测与识别模型)
>
> [3.2.1 GOT-OCR 2.0基本原理
> [19](#got-ocr-2.0基本原理)](#got-ocr-2.0基本原理)
>
> [3.2.2 微调原理 [22](#微调原理)](#微调原理)
>
> [3.2.3 SVD原理 [22](#svd原理)](#svd原理)
>
> [3.2.4 SVD低秩分解 [23](#svd低秩分解)](#svd低秩分解)
>
> [3.2.5 SVD的损失阈值调节 [24](#svd的损失阈值调节)](#svd的损失阈值调节)
>
> [3.3 实验结果及分析 [25](#实验结果及分析)](#实验结果及分析)
>
> [3.3.1 实验设计 [25](#实验设计)](#实验设计)
>
> [3.3.2 微调前后实验结果对比
> [26](#微调前后实验结果对比)](#微调前后实验结果对比)
>
> [3.3.3 SVD低秩分解实验结果对比
> [29](#svd低秩分解实验结果对比)](#svd低秩分解实验结果对比)
>
> [3.4 本章小结 [31](#本章小结-1)](#本章小结-1)

[4 铭牌检测与识别系统的设计与实现
[32](#铭牌检测与识别系统的设计与实现)](#铭牌检测与识别系统的设计与实现)

> [4.1 系统整体设计 [32](#系统整体设计)](#系统整体设计)
>
> [4.2 具体模块设计与实现
> [33](#具体模块设计与实现)](#具体模块设计与实现)
>
> [4.2.1 模型选择功能 [33](#模型选择功能)](#模型选择功能)
>
> [4.2.2 图片上传功能 [33](#图片上传功能)](#图片上传功能)
>
> [4.2.3 图片识别功能 [35](#图片识别功能)](#图片识别功能)
>
> [4.2.4 识别结果渲染功能 [35](#识别结果渲染功能)](#识别结果渲染功能)
>
> [4.3 本章小结 [37](#本章小结-2)](#本章小结-2)

[5 总结与展望 [38](#总结与展望)](#总结与展望)

> [5.1 研究总结 [38](#研究总结)](#研究总结)
>
> [5.2 展望 [38](#展望)](#展望)

[参考文献 [40](#_Toc199142651)](#_Toc199142651)

[谢辞 [43](#_Toc199142652)](#_Toc199142652)

# 引 言

## 课题背景与意义

随着电力行业的快速发展，电力设备的数量与种类不断增加。电力设备的铭牌记录着设备的型号、规格、参数等关键信息，所以对于设备的维护、管理以及电力系统的稳定运行有很重要的作用<sup>\[1\]</sup>。但传统的电力设备铭牌信息获取方式主要是依赖人工抄录，这种方式存在效率低下，易出现遗漏、出错的问题。而且因为人工抄录的成本较高，所以也很难得到足够真实数据<sup>\[2\]</sup>。这就无法满足电力行业快速发展的需求。

近年来计算机视觉和深度学习技术迅速发展，文本检测与识别技术取得了明显的进步。其中自然场景文本检测和识别任务是计算机视觉领域中热门的研究领域<sup>\[3\]</sup>。传统的光学字符识别技术（Optical
Character Recognition,
OCR）<sup>\[4\]</sup>，可以将图片、扫描件中的文字转化为可编辑的文本格式。它通过先对图像做预处理，再分割字符、提取特征并识别。常见的应用场景是日常生活中广泛应用的面向垂类的结构化文本识别，也即格式固定，文本整齐并且分布规律。因此很适合用OCR技术进行自动化文字识别<sup>\[5\]</sup>。

但与自然场景下的文本检测不同的是电力设备的铭牌上文本信息密集，包含中文、英文、数字及电力系统中特有的符号。同时由于铭牌大多数是由金属制作的，所以设备会受到阳光直射、逆光、阴影等不同光照情况的影响如图1.1(a)。在阳光直射时铭牌表面会出现光斑导致部分文本过曝而无法辨认<sup>\[6\]</sup>。在逆光情况下铭牌整体会处于较暗的状态，文本细节不容易看清<sup>\[6\]</sup>。在阴影区域图像对比度降低，字符与背景的区分度会变小。

部分电力设备位于高湿度、高盐度、沙尘等恶劣的自然环境中。在高湿度的环境下，铭牌容易受潮生锈，金属材质的铭牌表面会出现腐蚀斑点如图1.1(b)，这些斑点会覆盖部分文本字符从而影响识别效果<sup>\[7\]</sup>。在海边这种高盐度地区，铭牌长期受到盐雾侵蚀，不仅会加速铭牌的老化和损坏，还会使字符表面变得粗糙导致图像采集时出现反光不均匀的情况。沙尘环境中，沙尘颗粒会附着在铭牌表面，模糊文本字符，同样会增加文本识别的难度。

| <img src="C:\Users\Administrator\Desktop\media_gao/media/image3.jpeg"
style="width:2.84514in;height:1.39653in"
alt="图片包含 图形用户界面 AI 生成的内容可能不正确。" /> | <img src="C:\Users\Administrator\Desktop\media_gao/media/image4.jpeg"
style="width:2.56806in;height:1.39931in" /> |
|----|----|
| (a)受光照影响的电力设备铭牌图像 | (b)腐蚀生锈的铭牌图像 |

1.  电力设备真实铭牌采集图像

随着深度学习的兴起，卷积神经网络(Convolutional Neural Network,
CNN)<sup>\[8\]</sup>等深度学习模型被引入OCR领域。CNN强大的特征自动提取能力使OCR系统能自动从大量图像数据中学习字符特征而无需人工设计特征提取规则。它对不同字体、字号、光照条件、倾斜变形等复杂情况的适应能力大幅提升。这对电力设备资料科学、规范化的管理具有重要的意义，有助于推动电力行业的智能化发展并且提高电力系统的自动化水平和可靠性。

## 本文研究目标及内容

本文致力于开发适用于电力设备铭牌文本检测与识别的算法，通过构建数据样本、微调模型、模型压缩等方法，提升电力铭牌文本检测与识别的效率和准确率。在此基础上设计前端页面实现实际应用，以满足电力设备管理中对铭牌信息快速、准确提取的需求。

首先，为给GOT-OCR
2.0的优化奠定理论基础并在后续对优化结果做出评价，本文引入Transformers框架的相关原理，深入剖析注意力机制，包括自注意力的计算过程及在捕捉序列依赖关系上的优势，阐述编码器与解码器的结构组成与工作流程。围绕平均编辑距离、混淆矩阵、参数量、计算量等评价指标，分别描述其定义、计算方式及在评估模型性能方面的意义；

此外，通过数据集构建与模型优化实验，验证数据标准化与轻量化技术对电力铭牌文本检测识别精度与效率的提升作用。基于对电力设备铭牌文本检测与识别实际需求的调查，构建包含850张自然场景图像的电力设备铭牌数据集，对数据进行预处理、划分数据集，并建立标准化标注规范以确保数据质量与可用性，研究并优化基于GOT-OCR
2.0搭建的铭牌文本检测与识别模型，阐述其基本原理、微调原理和SVD原理，开展模型微调与SVD低秩分解的实验，通过对比微调前后、SVD低秩分解前后的模型预测结果，验证微调、低秩分解等优化对于模型在电力设备铭牌文本检测与识别性能的提升效果；

最后，设计系统实现电力铭牌文本检测识别的轻量化部署与可视化交互。基于前期构建的电力设备铭牌文本检测与识别模型，采用VUE框架实现铭牌检测与识别系统。系统可根据边缘设备的性能进行不同模型的选择，从本地或者直接拖动网页的图片上传，从而进行图片识别，并可以将结果以表格形式渲染展示，为电力设备铭牌信息的高效处理提供了便捷、直观的交互系统。


# 总结与展望

## 研究总结

针对电力设备铭牌图像背景复杂、小文本与密集参数识别难的问题，本文提出一种基于GOT-OCR
2.0框架的端到端检测与识别算法。该算法采用ViTDet图像编码器与Qwen文本解码器实现从图像到文本的特征映射，通过全参数微调机制对模型进行特定任务适配。在自制850张铭牌数据集上，将微调后模型与原始GOT-OCR
2.0模型对比，结果表明：本文方法在文本识别的F1值从64.56%提升至83.39%，准确率从58.14%提升至79.30%，召回率从78.11%提升至89.65%，编辑距离从0.6825降至0.2628，能够精准提取电力设备铭牌图像中的型号、参数等关键数据。

针对大语言模型存在的模型参数量大、边缘部署成本高的问题，本文提出基于SVD的线性层低秩分解算法。该算法对Qwen解码器中1024×1024维度的全连接层进行奇异值分解，引入动态损失阈值调节机制平衡精度与压缩率。在自制数据集上的实验结果表明：当损失阈值设为0.3时，模型计算量从1.4107GFlops下降至1.3386GFlops（降幅5.1%），参数量从0.5572B减少至0.5185B（降幅6.9%），F1值保持75.57%，准确率71.38%，召回率82.27%，在消费级GPU上的推理速度提升12.7%，实现了模型轻量化与性能保持的平衡。

基于微调后模型及SVD压缩模型，通过VUE框架实现铭牌检测与识别系统。系统涵盖模型选择、图片上传、图片识别和识别结果渲染等功能模块，支持边缘设备性能动态匹配模型，既可以在低算力设备上调用SVD压缩模型，提升预测效率，也可以在高性能GPU设备上调用全参数模型，识别准确率可达83.39%，支持多种图片上传方式，识别结果以表格形式直观展示，系统设计的交互界面直观友好，可一键完成铭牌图像的智能化解析，一定程度上解决了传统人工录入易出错、效率低的问题，在电力设备运维、回收等场景中具有工程应用价值。

## 展望

本文针对电力设备铭牌文本检测与识别技术开展研究并取得阶段性成果。所提出的铭牌识别算法可精准提取图像中的关键参数，基于SVD的模型压缩方法在维持较高识别精度的同时，有效降低了计算量与参数量。面向实际应用开发的铭牌识别系统，也切实改善了传统人工录入易出错、效率低的问题。受限于研究周期、实验条件及科研能力，本研究仍存在优化空间，未来可从以下方向深入探索：

在模型轻量化优化方面，尽管当前算法已具备较高准确率，但模型轻量化水平有待提升。后续研究可尝试引入剪枝、量化及知识蒸馏等技术，进一步减少模型参数并提升推理速度，以降低计算资源占用，使模型能在资源受限的边缘设备上高效运行。

数据集的规模与多样性拓展是另一重要方向。现有数据集虽覆盖多种电力设备及复杂场景，但随着电力技术迭代，新设备、新场景不断出现。未来需持续扩大数据集规模，广泛采集不同地区、厂家、年代的电力设备铭牌图像，尤其注重收集极端天气环境下及严重老化设备的铭牌样本，通过增强数据多样性，进一步提升模型的泛化能力与鲁棒性，确保其在各类复杂工况下均能稳定准确地完成检测与识别任务。

在系统功能完善层面，本文设计的系统虽采用模块化架构，具备较高可拓展性，但在算法与系统的深度集成方面仍有改进空间。后续可聚焦于提升系统的智能化与交互体验，例如引入智能语音交互模块，支持语音指令控制及识别结果语音播报功能，以适应运维人员在双手忙碌或嘈杂环境下的操作需求，进一步增强系统的实用性与用户友好性。
