import { useState, type ReactNode } from 'react'
import { Download, SlidersHorizontal } from 'lucide-react'
import type { Experiment } from '../types'
import { downloadUrl } from '../services/api'
import { displayValue } from '../services/presentation'
import { Chart, Modal, format } from './Common'
import { DataTable } from './DataTable'

const studyTables = [
  ['study_metrics','Three-experiment performance','A: original Traditional; B: reviewed Traditional; C: reviewed Enhanced. Same held-out observations.'],
  ['study_comparisons','Separate review and interaction effects','A vs B: review decisions. B vs C: interactions. A vs C: combined workflow.'],
  ['study_predictions','Three-experiment predictions','Actual waits, predictions, and raw errors for every experiment on the same test rows.'],
  ['original_coefficients','Original-data model coefficients','Coefficients of arm A, fitted before recorded review corrections or exclusions.'],
  ['original_model_checks','Original-data model checks','Rank, conditioning, and training rows for arm A.'],
  ['source_notes','Workbook source notes','Declarations supplied with the original workbook, not independently verified evidence.'],
  ['research_documentation','Research documentation','Source status, observation definition, and researcher rationales recorded for this run.'],
]
const tables = [
  ['coefficients','Model coefficients','Technical values showing how each variable contributes to the prediction, including the starting value (intercept).'],
  ['interaction_coefficients','Combined-factor coefficients','How combinations of variables contribute to the prediction.'],
  ['selected_interactions','Combined factors (interaction terms)','The researcher-approved combinations used by the enhanced model.'],
  ['iqr_bounds','Unusual-value limits (IQR)','IQR describes the spread of the middle half of the training data. These limits flag unusual values for review.'],
  ['iqr_flags','Unusual observations','Flagged observations are reviewed, not automatically removed.'],
  ['review_audit','Review decisions','The recorded reasons for keeping, correcting, or excluding observations.'],
  ['reviewed_training','Data used for training','Training observations after recorded review decisions.'],
  ['split_membership','Training and evaluation groups','Which observations were used to learn and which were kept aside to evaluate predictions.'],
  ['category_encoding','Encoded variables','How text categories were represented numerically for the models.'],
  ['severity_thresholds','Station condition thresholds','Quartiles and directions learned only from reviewed training data.'],
  ['category_evidence','Category scoring evidence','Training category means, scoring rules, and any configured overrides.'],
  ['predictions','All prediction results','Actual waits, predictions, errors, and the seven-factor station scores.'],
  ['comparison','Model comparison differences','The differences between the models on the same evaluation observations.'],
  ['model_diagnostics','Model checks','Technical checks on model fitting and data suitability.'],
  ['original_training','Original training observations','Training data before any review changes.'],
  ['original_test','Evaluation observations','Observations kept aside from training to check the predictions.'],
]
export function ResearchDetails({s, children, advanced}: {s:Experiment; children?: ReactNode; advanced?: ReactNode}) {
  const availableTables = s.study_available ? [...studyTables, ...tables] : tables
  const [open,setOpen]=useState(false)
  const [advancedLoaded,setAdvancedLoaded]=useState(false)
  const [table,setTable]=useState('coefficients')
  const [figures,setFigures]=useState(false)
  const close = () => {setOpen(false);setAdvancedLoaded(false);setFigures(false)}
  return <><button className="button details-trigger" onClick={()=>setOpen(true)}><SlidersHorizontal size={16}/>View Details</button>
    {open && <Modal title="Analysis Details" className="wide-modal research-details-modal" close={close}>
      <div className="modal-body research-details">
        {children}
        <details className="disclosure advanced-research" onToggle={e=>{if(e.currentTarget.open)setAdvancedLoaded(true)}}>
          <summary>Advanced Research Details</summary>
          {advancedLoaded && <div className="disclosure-body">
            <p className="section-caption">Optional evidence for reviewing or documenting the analysis. You do not need these technical values to read the main result.</p>
            {advanced}
            <h3>How the data was used</h3>
            <dl className="research-facts"><div><dt>Training observations</dt><dd>{s.reviewed_training} used / {s.training} original</dd></div><div><dt>Evaluation observations</dt><dd>{s.test}</dd></div><div><dt>Test fraction / random seed</dt><dd>{s.config.test_size} / {s.config.random_state}</dd></div><div><dt>IQR bounds</dt><dd>Q1 - {s.config.iqr_multiplier} x IQR; Q3 + {s.config.iqr_multiplier} x IQR</dd></div><div><dt>Classification wait bounds (min)</dt><dd>{s.config.wait_thresholds.join(' / ')}</dd></div><div><dt>Overall score boundaries</dt><dd>{s.config.station_thresholds.join(' / ')}</dd></div></dl>
            <p className="section-caption"><strong>IQR (interquartile range)</strong> describes the spread of the middle half of the training data. It helps identify unusual observations for review; a flag does not automatically remove a row.</p>
            <p className="section-caption"><strong>Interaction terms</strong> let the enhanced model consider selected factors together. Only researcher-approved combinations are used.</p>
            <p className="section-caption">MSE = sum of squared errors / number of observations. RMSE = square root of MSE. Both use raw predictions on the same {s.test} evaluation observations. Evaluation data does not determine training thresholds.</p>
            <p className="section-caption">The main B vs C comparison uses the same reviewed training rows and isolates interaction effects. The additional A vs B comparison examines recorded review decisions using an original-data baseline.</p>
            <label className="research-table-select">Explore research data<select aria-label="Research table" aria-describedby="research-table-help" value={table} onChange={e=>setTable(e.target.value)}>{availableTables.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
            <p id="research-table-help" className="section-caption">{availableTables.find(([id])=>id===table)?.[2]}</p>
            <DataTable s={s} name={table}/>
            <details className="disclosure"><summary>Station conditions across observations</summary><div className="disclosure-body"><table aria-label="Classification distribution"><thead><tr><th>Condition</th><th>Observations</th></tr></thead><tbody>{Object.entries(s.distribution).map(([label,count])=><tr key={label}><td>{String(displayValue(label))}</td><td>{count}</td></tr>)}</tbody></table></div></details>
            <details className="disclosure" onToggle={e=>setFigures(e.currentTarget.open)}><summary>Research figures</summary>{figures && <div className="research-figures">{s.figures.map(name=><Chart key={name} s={s} name={name} title={name.replaceAll('_',' ').replace('baseline','Traditional MLR')}/>)}</div>}</details>
            {s.warnings.length>0 && <details className="disclosure"><summary>Model notes & limitations ({s.warnings.length})</summary><ul className="warning-list">{s.warnings.map(text=><li key={text}>{text.replaceAll('Baseline','Traditional')}</li>)}</ul></details>}
          </div>}
        </details>
      </div>
    </Modal>}
  </>
}

export function ExportResults({s}: {s:Experiment}) {
  const availableTables = s.study_available ? [...studyTables, ...tables] : tables
  const [open,setOpen]=useState(false)
  const [table,setTable]=useState('predictions')
  return <><button className="button export-trigger" onClick={()=>setOpen(true)}><Download size={16}/>Export Results</button>{open && <Modal title="Export Results" close={()=>setOpen(false)}><div className="modal-body"><p className="muted">{s.name} · {format(s.records)} observations</p><a className="button primary export-workbook" href={downloadUrl(s,'excel')}><Download size={16}/>Download Excel workbook</a><p className="section-caption">Includes all transport modes in this experiment, reviewed observations, decisions, predictions, errors, MSE/RMSE, coefficients, selected interactions, severity scores, and station classifications.</p><details className="disclosure"><summary>Other formats & reproducibility files</summary><div className="disclosure-body"><label>CSV table<select aria-label="CSV table" value={table} onChange={e=>setTable(e.target.value)}>{[['metrics','Model metrics'],...availableTables].map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label><a className="button small" href={downloadUrl(s,'csv',table)}>Download CSV</a><div className="export-links"><a href={downloadUrl(s,'bundle')}>Complete bundle (.zip)</a><a href={downloadUrl(s,'config')}>Analysis configuration (.json)</a><a href={downloadUrl(s,'reviews')}>Review decisions (.json)</a></div></div></details><p className="section-caption">Traditional MLR is labeled “Baseline MLR” in the research files. Undefined classifications are labeled “Pending configuration”; both mean Requires Researcher Decision. Downloaded charts use light backgrounds for reports.</p></div></Modal>}</>
}
