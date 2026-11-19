"""Build a separate illustrated study guide; never modifies the thesis or data."""
from __future__ import annotations

import csv
import json
import math
import re
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
import pymupdf
from PIL import Image
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/chapter_3_to_5_plain_language_guide_2026-11-20"
ASSETS = OUT / "assets"
DOWNLOADS = Path.home() / "Downloads"
RUN = ROOT / "outputs/20261119T145502_187046Z_a4706e"
CONTENT = ROOT / "scripts/chapter_3_to_5_guide_content.md"
STEM = "Chapters_3_to_5_Illustrated_Study_Guide"
NAVY = "17344F"
TEAL = "117C83"
GOLD = "CE8B26"
INK = "233746"
MUTED = "526776"
LIGHT = "EDF5F7"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                     "axes.spines.top": False, "axes.spines.right": False})


def canvas(name, h=3.3):
    fig, ax = plt.subplots(figsize=(11, h))
    ax.set(xlim=(0, 11), ylim=(0, h))
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, body="", color=TEAL, fs=12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                              facecolor="#"+LIGHT, edgecolor="#"+color, linewidth=1.6))
    ax.text(x+w/2, y+h-.28, title, ha="center", va="center", weight="bold",
            color="#"+color, fontsize=fs+1)
    if body:
        ax.text(x+w/2, y+h/2-.12, body, ha="center", va="center", color="#"+INK,
                fontsize=fs, linespacing=1.45)


def arrow(ax, start, end, color=MUTED):
    ax.annotate("", xy=end, xytext=start,
                arrowprops={"arrowstyle": "-|>", "lw": 2, "color": "#"+color})


def save(fig, name):
    fig.savefig(ASSETS/name, dpi=190, bbox_inches="tight", facecolor="white", pad_inches=.12)
    plt.close(fig)


def read_csv(name):
    with (RUN/'csv'/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def result_canvas(title, height=4.4):
    fig, ax=plt.subplots(figsize=(9,height))
    ax.set_title(title,fontsize=16,weight='bold',pad=14,color='#'+NAVY)
    ax.tick_params(labelsize=12)
    ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.text(.99,.015,'EXISTING PROTOTYPE • SYNTHETIC DATA',ha='right',fontsize=9,color='#'+MUTED)
    return fig,ax


def readable_result_figures():
    """Redraw saved results for legibility, without fitting or changing any model."""
    metrics={r['Arm']:r for r in read_csv('study_metrics.csv')}
    n=int(metrics['A']['Training Rows'])
    flags=read_csv('iqr_flags.csv');flagged=len({r['Record ID'] for r in flags})
    fig,ax=result_canvas('IQR screening of training observations')
    bars=ax.bar(['Not flagged','Flagged for review'],[n-flagged,flagged],color=['#117C83','#CE8B26'])
    ax.set_ylabel('Number of training records',fontsize=13);ax.set_ylim(0,n*1.15)
    ax.bar_label(bars,padding=5,fontsize=15)
    fig.tight_layout(rect=(0,.045,1,1));save(fig,'iqr_screening.png')

    for metric,unit,file in [('MSE','min²','mse.png'),('RMSE','minutes','rmse.png')]:
        vals=[float(metrics[a][metric]) for a in ['B','C']]
        fig,ax=result_canvas('Held-out '+metric+' comparison')
        bars=ax.bar(['Arm B\nAdditive baseline','Arm C\nEnhanced MLR'],vals,color=['#2B64A1','#117C83'],width=.57)
        ax.set_ylabel(f'{metric} ({unit})',fontsize=13);ax.set_ylim(0,max(vals)*1.22)
        ax.bar_label(bars,labels=[f'{v:.4f}' for v in vals],padding=7,fontsize=15)
        fig.tight_layout(rect=(0,.045,1,1));save(fig,file)

    folds=read_csv('cv_folds.csv')
    fig,ax=result_canvas('Cross-validation MSE across 50 folds')
    result=ax.boxplot([[float(r['Baseline MSE']) for r in folds],[float(r['Enhanced MSE']) for r in folds]],
                       tick_labels=['Arm B\nAdditive baseline','Arm C\nEnhanced MLR'],patch_artist=True,
                       widths=.47,medianprops={'color':'#CE8B26','linewidth':2.3})
    for patch,color in zip(result['boxes'],['#8AAECF','#7BBEB8']):patch.set_facecolor(color)
    ax.set_ylabel('Validation MSE (min²)',fontsize=13)
    fig.tight_layout(rect=(0,.045,1,1));save(fig,'cv_mse.png')

    predictions=read_csv('predictions.csv')
    actual=np.array([float(r['Actual Waiting Time']) for r in predictions])
    predicted=np.array([float(r['Enhanced Predicted Waiting Time']) for r in predictions])
    fig,ax=result_canvas('Target waiting time versus prediction')
    ax.scatter(actual,predicted,s=38,facecolor='#65AAA6',edgecolor='#117C83',alpha=.85)
    lo=min(actual.min(),predicted.min());hi=max(actual.max(),predicted.max())
    ax.plot([lo,hi],[lo,hi],'--',color='#76818A',lw=2,label='Perfect agreement')
    ax.set_xlabel('Target waiting time in dataset (minutes)',fontsize=12)
    ax.set_ylabel('Raw Arm C prediction (minutes)',fontsize=12);ax.legend(fontsize=11)
    fig.tight_layout(rect=(0,.045,1,1));save(fig,'actual_vs_enhanced.png')

    fig,ax=result_canvas('Residuals versus predicted waiting time')
    ax.scatter(predicted,actual-predicted,s=38,facecolor='#65AAA6',edgecolor='#117C83',alpha=.85)
    ax.axhline(0,ls='--',color='#76818A',lw=2)
    ax.set_xlabel('Raw Arm C prediction (minutes)',fontsize=12)
    ax.set_ylabel('Residual: target − prediction (minutes)',fontsize=12)
    fig.tight_layout(rect=(0,.045,1,1));save(fig,'residuals_enhanced.png')

    rows=read_csv('classification_confusion.csv')
    cols=[k for k in rows[0] if k!='Label from actual wait']
    matrix=np.array([[int(r[k]) for k in cols] for r in rows])
    counts=matrix.sum(axis=0)
    labels=['Normal\nOperation','Minor\nDelay','Moderate\nDelay','Severe\nDelay','Pending\nconfiguration']
    fig,ax=result_canvas('Condition labels for held-out observations')
    bars=ax.bar(labels,counts,color=['#117C83','#D7B14C','#D98E43','#B85353','#919CA3'],width=.7)
    ax.bar_label(bars,padding=5,fontsize=15);ax.set_ylim(0,max(counts)*1.22)
    ax.set_ylabel('Number of test observations',fontsize=13);ax.tick_params(axis='x',labelsize=11)
    fig.tight_layout(rect=(0,.045,1,1));save(fig,'station_classifications.png')

    fig,ax=result_canvas('Condition-label agreement',5.3)
    ax.grid(False);ax.imshow(matrix,cmap='Blues',vmin=0,vmax=matrix.max(),aspect='auto')
    ax.set_xticks(range(5),labels,fontsize=11);ax.set_yticks(range(5),labels,fontsize=11)
    ax.set_xlabel('Label using predicted wait',fontsize=12,labelpad=10)
    ax.set_ylabel('Label using dataset target wait',fontsize=12)
    for i in range(5):
        for j in range(5):
            ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=17,
                    color='white' if matrix[i,j]>matrix.max()*.6 else '#233746')
    fig.tight_layout(rect=(0,.045,1,1));save(fig,'classification_agreement.png')


def make_assets():
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig, ax = canvas("story", 2.7)
    for x, title, body in [(0.1,"CHAPTER 3", "How the study works\nThe method and fair comparison"),
                            (3.85,"CHAPTER 4", "What the experiment found\nThe figures and measured errors"),
                            (7.6,"CHAPTER 5", "What the findings mean\nConclusions and next steps")]:
        box(ax,x,.35,3.25,1.9,title,body,fs=11)
    arrow(ax,(3.45,1.3),(3.72,1.3));arrow(ax,(7.2,1.3),(7.47,1.3))
    save(fig,"chapter_story.png")

    fig, ax=canvas("arms",4.1)
    box(ax,.15,1.1,2.5,2.1,"ONE DATASET","Set aside the test set\nbefore learning anything",fs=11)
    for y,title,body,col in [(2.95,"ARM A","Original training + additive MLR",NAVY),
                              (1.65,"ARM B","Reviewed training + additive MLR",TEAL),
                              (.35,"ARM C","Reviewed training + interactions",GOLD)]:
        box(ax,3.25,y,4.2,.85,title,body,col,10)
        arrow(ax,(2.72,2.15),(3.15,y+.4))
        arrow(ax,(7.55,y+.4),(8.2,2.15))
    box(ax,8.3,1.1,2.45,2.1,"SAME TEST SET","Compare errors\nfor the same observations",fs=10)
    save(fig,"three_arms.png")

    fig,ax=canvas("timeline",3.1)
    ax.plot([.7,10.25],[1.25,1.25],color="#"+NAVY,lw=3)
    for x,t,desc in [(1,"07:00","Start counting"),(7.4,"08:00","Passenger arrives"),(10,"08:12","Passenger boards")]:
        ax.scatter(x,1.25,s=70,c="#"+TEAL,zorder=4)
        ax.text(x,.9,t,ha="center",weight="bold",fontsize=15)
        ax.text(x,.53,desc,ha="center",fontsize=11)
    for x,t in [(2.6,"07:15"),(4.2,"07:30"),(5.8,"07:45")]:
        ax.plot([x,x],[1.12,1.38],color="#"+NAVY)
        ax.text(x,.9,t,ha="center",fontsize=10)
    box(ax,1,1.75,6.4,.85,"PRECEDING 60 MINUTES","Passenger arrivals + vehicles serving this route/direction",fs=10)
    box(ax,7.65,1.75,2.85,.85,"12-MINUTE WAIT","08:12 minus 08:00",GOLD,10)
    save(fig,"passenger_timeline.png")

    fig,ax=canvas("split",3.4)
    box(ax,.15,1.05,2.1,1.35,"100 RECORDS","Illustration only",fs=11)
    box(ax,3.05,1.85,4.1,1.15,"80 TRAINING RECORDS","Learn fences, encoding, rules and models",fs=10)
    box(ax,3.05,.2,4.1,1.15,"20 TEST RECORDS","Keep untouched until evaluation",GOLD,10)
    arrow(ax,(2.35,1.75),(2.95,2.4));arrow(ax,(2.35,1.65),(2.95,.8))
    box(ax,8,1.05,2.8,1.35,"FINAL CHECK","Predict test waits\nthen compare with actuals",fs=10)
    arrow(ax,(7.25,2.4),(7.9,1.9));arrow(ax,(7.25,.8),(7.9,1.45))
    save(fig,"train_test_split.png")

    fig,ax=plt.subplots(figsize=(10.8,3.2))
    ax.set(xlim=(0,29),ylim=(-.7,1.2),yticks=[],xlabel="Waiting time (minutes) — teaching example")
    ax.spines['left'].set_visible(False)
    ax.plot([2,18],[.35,.35],color="#"+NAVY,lw=2)
    ax.add_patch(Rectangle((8,.08),4,.54,facecolor="#8CC8CC",edgecolor="#"+TEAL,lw=2))
    ax.plot([10,10],[.08,.62],color="#"+NAVY,lw=2)
    for x,label in [(2,"Lower fence\n2 min"),(8,"Q1 = 8"),(12,"Q3 = 12"),(18,"Upper fence\n18 min")]:
        ax.plot([x,x],[-.05,.75],color="#"+MUTED,ls="--",lw=1)
        ax.text(x,.88,label,ha="center",fontsize=11)
    ax.scatter(26,.35,c="#"+GOLD,s=110,zorder=4)
    ax.text(26,.85,"26 min\nFlag for review",ha="center",color="#925C13",fontsize=12)
    ax.text(10,-.35,"Middle 50%: IQR = 4",ha="center",fontsize=12)
    save(fig,"iqr_example.png")

    fig,axs=plt.subplots(1,2,figsize=(11,3.4),sharey=True)
    x=np.array([100,200,300,400,500])
    for ax,period,slopes in zip(axs,["Off-peak illustration","Peak-period illustration"],[(.025,.012),(.045,.018)]):
        ax.plot(x,5+slopes[0]*x,label="Fewer vehicles",color="#"+GOLD,lw=2.5)
        ax.plot(x,5+slopes[1]*x,label="More vehicles",color="#"+TEAL,lw=2.5)
        ax.set(title=period,xlabel="Passenger volume (preceding hour)",ylim=(0,30))
        ax.grid(alpha=.15);ax.legend(fontsize=9)
    axs[0].set_ylabel("Illustrative waiting time (minutes)")
    fig.tight_layout()
    save(fig,"interaction_teaching.png")

    fig,ax=canvas("cv",3.3)
    colors=["6DA7BD","B6D8E3","CEDFE4","A8C9D3","81ADB9"]
    for row in range(5):
        ax.text(.1,2.85-row*.5,f"Round {row+1}",va="center",fontsize=11)
        for col in range(5):
            x=1.7+col*1.45;y=2.65-row*.5
            ax.add_patch(Rectangle((x,y),1.3,.38,facecolor="#"+(GOLD if col==row else colors[col]),edgecolor='white'))
            ax.text(x+.65,y+.19,"Check" if col==row else "Fit",ha='center',va='center',fontsize=10,color='white' if col==row else '#17344F')
    ax.text(9.25,1.8,"5 folds\n× 10 repeats\n= 50 comparisons",ha="center",va="center",fontsize=12,weight="bold",color="#"+TEAL)
    ax.text(5.1,.1,"All of this happens inside the training partition. The final test set stays separate.",ha='center',fontsize=10)
    save(fig,"cross_validation.png")

    fig,ax=plt.subplots(figsize=(11,3.3))
    labels=["Traffic","Weather","Passenger\nvolume","Route\ndistance","Vehicle\nfrequency","Time\nof day","Predicted\nwait"]
    vals=[2,1,3,1,2,2,1]
    ax.bar(labels,vals,color=["#117C83"]*6+["#CE8B26"],width=.65)
    ax.set(ylim=(0,3.75),yticks=[0,1,2,3],ylabel="Severity score")
    ax.text(3,3.5,"(2 + 1 + 3 + 1 + 2 + 2 + 1) / 7 = 1.714 → Moderate Delay",ha="center",weight="bold",color="#"+NAVY,fontsize=12)
    ax.grid(axis="y",alpha=.14);ax.set_axisbelow(True)
    fig.tight_layout();save(fig,"seven_factor_example.png")

    fig,ax=canvas("conclusions",3.4)
    for y,q,e,c in [(2.35,"Did review help?","Compare A and B","State the observed review effect"),
                     (1.3,"Did interactions help?","Compare B and C","State errors and uncertainty"),
                     (.25,"Can outputs be interpreted?","Inspect seven-factor scores","Describe labels and their limits")]:
        box(ax,.1,y,3.1,.78,"QUESTION",q,fs=9)
        box(ax,3.85,y,3.1,.78,"EVIDENCE",e,fs=9)
        box(ax,7.6,y,3.1,.78,"CONCLUSION",c,fs=9)
        arrow(ax,(3.3,y+.39),(3.75,y+.39));arrow(ax,(7.05,y+.39),(7.5,y+.39))
    save(fig,"conclusion_chain.png")

    # Recover the original Figure 3.1 directly, without changing its contents.
    pdf=pymupdf.open(str(DOWNLOADS/'Raymart - Revised (highlighted).pdf'))
    for im in pdf[52].get_images(full=True):
        if im[2]==1158 and im[3]==548:
            image=pdf.extract_image(im[0]);(ASSETS/'original_figure_3_1.png').write_bytes(image['image'])
            break
    else:
        pdf[52].get_pixmap(matrix=pymupdf.Matrix(3,3),clip=pymupdf.Rect(114,441,534,641)).save(str(ASSETS/'original_figure_3_1.png'))
    source=DOWNLOADS/'Chapter 4 Figures (VALIDATION)'
    for name in ['iqr_screening.png','mse.png','rmse.png','cv_mse.png','actual_vs_enhanced.png',
                 'station_classifications.png','classification_agreement.png','residuals_enhanced.png','interaction_01.png']:
        shutil.copy2(source/name,ASSETS/name)
    readable_result_figures()


def shade(cell, fill):
    pr=cell._tc.get_or_add_tcPr();node=OxmlElement('w:shd');node.set(qn('w:fill'),fill);pr.append(node)


def runs(p,text):
    for part in re.split(r'(\*\*.*?\*\*)',text):
        if not part:continue
        r=p.add_run(part[2:-2] if part.startswith('**') and part.endswith('**') else part)
        r.bold=part.startswith('**') and part.endswith('**')


def set_cell_margins(cell):
    pr=cell._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
    for s in ['top','left','bottom','right']:
        v=OxmlElement('w:'+s);v.set(qn('w:w'),'85');v.set(qn('w:type'),'dxa');m.append(v)
    pr.append(m)


def add_table(doc, lines):
    parsed=[[c.strip() for c in l.strip().strip('|').split('|')] for l in lines]
    parsed=[r for r in parsed if not all(re.fullmatch(r'[:\- ]+',c or '-') for c in r)]
    table=doc.add_table(rows=0, cols=len(parsed[0]));table.alignment=WD_TABLE_ALIGNMENT.CENTER
    table.autofit=False
    widths={2:[2.05,4.88],3:[1.5,2.5,2.93],4:[1.0,1.98,1.98,1.97],5:[1.05,1.47,1.47,1.47,1.47],7:[.4,.8,.8,1.25,1.23,1.23,1.22]}.get(len(parsed[0]))
    if widths:
        for col,w in zip(table.columns,widths):col.width=Inches(w)
    for ri,row in enumerate(parsed):
        cells=table.add_row().cells
        trpr=table.rows[-1]._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
        if ri==0:
            repeat=OxmlElement('w:tblHeader');repeat.set(qn('w:val'),'true');trpr.append(repeat)
        for ci,text in enumerate(row):
            c=cells[ci];c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;set_cell_margins(c)
            if widths:c.width=Inches(widths[ci])
            p=c.paragraphs[0];p.paragraph_format.space_after=Pt(0);p.paragraph_format.space_before=Pt(0)
            p.paragraph_format.line_spacing=1.05
            runs(p,text)
            for r in p.runs:
                r.font.size=Pt(9.5 if len(row)>4 else 10)
                if ri==0:r.bold=True;r.font.color.rgb=RGBColor.from_string('FFFFFF')
            shade(c,NAVY if ri==0 else ('F0F5F7' if ri%2 else 'FFFFFF'))
    doc.add_paragraph().paragraph_format.space_after=Pt(0)


def image(doc,path,caption):
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after=Pt(3);p.paragraph_format.keep_with_next=True
    with Image.open(path) as im:w,h=im.size
    maxh=3.25
    if path.name in ['iqr_screening.png','mse.png','rmse.png','cv_mse.png','actual_vs_enhanced.png',
                     'station_classifications.png','classification_agreement.png','residuals_enhanced.png']:
        maxh=3.75
    if path.name in ['original_figure_3_1.png','three_arms.png']:maxh=3.05
    width=min(6.93,maxh*w/h)
    p.add_run().add_picture(str(path),width=Inches(width))
    c=doc.add_paragraph(style='Caption');c.paragraph_format.keep_with_next=False
    c.paragraph_format.space_after=Pt(8);c.add_run(caption)


def build_doc():
    doc=Document();s=doc.sections[0]
    s.page_width=Inches(8.27);s.page_height=Inches(11.69)
    s.top_margin=Inches(.66);s.bottom_margin=Inches(.65);s.left_margin=Inches(.67);s.right_margin=Inches(.67)
    s.header_distance=Inches(.25);s.footer_distance=Inches(.25)
    styles=doc.styles
    normal=styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(11)
    normal.font.color.rgb=RGBColor.from_string(INK)
    normal.paragraph_format.space_after=Pt(7);normal.paragraph_format.line_spacing=1.12
    for name,size,color in [('Title',29,NAVY),('Subtitle',13,MUTED),('Heading 1',21,NAVY),('Heading 2',12.5,TEAL),('Heading 3',11.5,TEAL)]:
        st=styles[name];st.font.name='Calibri';st.font.size=Pt(size);st.font.color.rgb=RGBColor.from_string(color)
        st.font.bold=name not in ['Subtitle'];st.paragraph_format.space_before=Pt(9);st.paragraph_format.space_after=Pt(7)
        st.paragraph_format.keep_with_next=True
    styles['Caption'].font.name='Calibri';styles['Caption'].font.size=Pt(9)
    styles['Caption'].font.color.rgb=RGBColor.from_string(MUTED);styles['Caption'].font.italic=True
    for name in ['List Bullet','List Number']:
        styles[name].font.name='Calibri';styles[name].font.size=Pt(11)
        styles[name].paragraph_format.space_after=Pt(6)
    header=s.header.paragraphs[0];header.text='MLR THESIS  /  ILLUSTRATED STUDY GUIDE  /  CHAPTERS 3–5'
    header.runs[0].font.size=Pt(8);header.runs[0].font.color.rgb=RGBColor.from_string(MUTED)
    footer=s.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    r=footer.add_run('Study guide • 20 November 2026  |  ');r.font.size=Pt(8)
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
    doc.core_properties.title='Chapters 3–5: Illustrated Plain-Language Study Guide'
    doc.core_properties.subject='Enhanced MLR for train and bus waiting-time prediction'
    doc.core_properties.author='Study guide prepared for Clarence'
    doc.core_properties.comments='Separate explanatory guide. Original thesis and datasets are unchanged.'
    text=CONTENT.read_text(encoding='utf-8')
    pages=text.split('\n---PAGE---\n')
    inventory=[]
    for pi,section in enumerate(pages):
        if pi:doc.add_page_break()
        lines=section.strip().splitlines();i=0
        while i<len(lines):
            ln=lines[i].strip()
            if not ln:i+=1;continue
            if ln.startswith('|'):
                rows=[]
                while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i]);i+=1
                add_table(doc,rows);continue
            if ln.startswith('# '):
                title=ln[2:];inventory.append({'planned_page':pi+1,'title':title})
                p=doc.add_paragraph(title,style='Title' if pi==0 else 'Heading 1')
            elif ln.startswith('## '):doc.add_paragraph(ln[3:],style='Heading 2')
            elif ln.startswith('### '):doc.add_paragraph(ln[4:],style='Heading 3')
            elif ln.startswith('Source:') or ln.startswith('Status:'):
                p=doc.add_paragraph();p.paragraph_format.space_after=Pt(8)
                r=p.add_run(ln);r.font.size=Pt(9);r.font.color.rgb=RGBColor.from_string(MUTED)
            elif ln.startswith('!['):
                m=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',ln)
                if not m:raise ValueError(ln)
                image(doc,OUT/m[2],m[1])
            elif ln.startswith('> '):
                p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.12)
                p.paragraph_format.right_indent=Inches(.12);p.paragraph_format.space_before=Pt(5)
                pr=p._p.get_or_add_pPr();sh=OxmlElement('w:shd');sh.set(qn('w:fill'),LIGHT);pr.append(sh)
                runs(p,ln[2:])
            elif ln.startswith('- '):runs(doc.add_paragraph(style='List Bullet'),ln[2:])
            elif re.match(r'^\d+\. ',ln):runs(doc.add_paragraph(style='List Number'),re.sub(r'^\d+\. ','',ln))
            else:
                para=[ln]
                while i+1<len(lines) and lines[i+1].strip() and not re.match(r'^(#|\||!\[|> |[-] |\d+\. |Source:|Status:)',lines[i+1].strip()):
                    i+=1;para.append(lines[i].strip())
                runs(doc.add_paragraph(),' '.join(para))
            i+=1
    # Prevent a blank page-break paragraph from keeping the following page with it.
    dest=OUT/(STEM+'.docx');doc.save(dest)
    shutil.copy2(dest,DOWNLOADS/dest.name)
    shutil.copy2(CONTENT,OUT/(STEM+'.md'))
    meta={'source_manuscript':str(DOWNLOADS/'Raymart - Revised (highlighted).docx'),
          'source_run':str(RUN),'run_data_status':'synthetic prototype',
          'planned_pages':len(pages),'word_count':len(re.findall(r'\b[\w’]+\b',text)),
          'embedded_images':len(doc.inline_shapes),'native_tables':len(doc.tables),
          'sections':inventory,'output':str(dest)}
    (OUT/'build_summary.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in meta.items() if k!='sections'},indent=2))


if __name__=='__main__':
    make_assets();build_doc()
