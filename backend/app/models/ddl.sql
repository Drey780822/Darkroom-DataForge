-- ============================================================
-- DARKROOM DATAFORGE — RELATIONAL SCHEMA DDL
-- Wits–merSETA Darkroom Document Intelligence Workstation
-- ============================================================

-- ============================================================
-- 1. PARENT ENTITY TABLE: qualifications
-- ============================================================
CREATE TABLE IF NOT EXISTS qualifications (
    saqa_id                 TEXT PRIMARY KEY,
    qualification_number    TEXT NOT NULL,
    qualification_name      TEXT NOT NULL,
    qualification_name_raw  TEXT NOT NULL,
    nqf_level               TEXT,
    nqf_sub_framework       TEXT NOT NULL,
    nsfas_allowance         TEXT NOT NULL,
    source_section          TEXT NOT NULL,
    source_page             TEXT NOT NULL,
    confidence              TEXT NOT NULL,
    extraction_note         TEXT,
    job_id                  TEXT,
    document_id             TEXT,
    CONSTRAINT chk_nsfas_allowance   CHECK (nsfas_allowance IN ('YES','NO')),
    CONSTRAINT chk_confidence        CHECK (confidence IN ('high','medium','low')),
    CONSTRAINT chk_nqf_sub_framework CHECK (nqf_sub_framework IN ('OQSF','HEQSF','GFETQSF')),
    CONSTRAINT fk_qual_job FOREIGN KEY (job_id) REFERENCES extraction_jobs(id) ON DELETE SET NULL,
    CONSTRAINT fk_qual_doc FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_qual_job_id ON qualifications(job_id);
CREATE INDEX IF NOT EXISTS idx_qual_document_id ON qualifications(document_id);

-- ============================================================
-- 2. DIMENSION TABLE: colleges
-- ============================================================
CREATE TABLE IF NOT EXISTS colleges (
    college_id           TEXT PRIMARY KEY,
    college_name         TEXT NOT NULL UNIQUE,
    data_quality_flag    TEXT,
    data_quality_note    TEXT,
    CONSTRAINT chk_college_quality_flag
        CHECK (data_quality_flag IS NULL OR data_quality_flag IN ('review_possible_variant'))
);

-- ============================================================
-- 3. JUNCTION TABLE: qualification_colleges (1:N relation)
-- ============================================================
CREATE TABLE IF NOT EXISTS qualification_colleges (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    saqa_id                TEXT NOT NULL,
    qualification_number   TEXT NOT NULL,
    college_id             TEXT NOT NULL,
    college_name           TEXT NOT NULL,
    source_section         TEXT NOT NULL,
    source_page            TEXT NOT NULL,
    job_id                 TEXT,
    document_id            TEXT,
    CONSTRAINT fk_qc_qualification
        FOREIGN KEY (saqa_id) REFERENCES qualifications(saqa_id) ON DELETE CASCADE,
    CONSTRAINT fk_qc_college
        FOREIGN KEY (college_id) REFERENCES colleges(college_id) ON DELETE RESTRICT,
    CONSTRAINT fk_qc_job FOREIGN KEY (job_id) REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_qc_doc FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    CONSTRAINT uq_qc_pair UNIQUE (saqa_id, college_id)
);
CREATE INDEX IF NOT EXISTS idx_qc_saqa_id   ON qualification_colleges(saqa_id);
CREATE INDEX IF NOT EXISTS idx_qc_college_id ON qualification_colleges(college_id);
CREATE INDEX IF NOT EXISTS idx_qc_job_id     ON qualification_colleges(job_id);

-- ============================================================
-- 4. SECONDARY RELATION TABLE: dspp_centres_of_specialisation
-- ============================================================
CREATE TABLE IF NOT EXISTS dspp_centres_of_specialisation (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    saqa_id                TEXT NOT NULL,
    qualification_number   TEXT NOT NULL,
    college_id             TEXT NOT NULL,
    college_name           TEXT NOT NULL,
    source_section         TEXT NOT NULL,
    source_page            TEXT NOT NULL,
    programme_context      TEXT NOT NULL,
    job_id                 TEXT,
    document_id            TEXT,
    CONSTRAINT fk_dspp_qualification
        FOREIGN KEY (saqa_id) REFERENCES qualifications(saqa_id) ON DELETE CASCADE,
    CONSTRAINT fk_dspp_college
        FOREIGN KEY (college_id) REFERENCES colleges(college_id) ON DELETE RESTRICT,
    CONSTRAINT fk_dspp_job FOREIGN KEY (job_id) REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_dspp_doc FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    CONSTRAINT uq_dspp_pair UNIQUE (saqa_id, college_id)
);
CREATE INDEX IF NOT EXISTS idx_dspp_saqa_id    ON dspp_centres_of_specialisation(saqa_id);
CREATE INDEX IF NOT EXISTS idx_dspp_college_id ON dspp_centres_of_specialisation(college_id);
CREATE INDEX IF NOT EXISTS idx_dspp_job_id     ON dspp_centres_of_specialisation(job_id);

-- ============================================================
-- 5. DATA DICTIONARY: data_dictionary
-- ============================================================
CREATE TABLE IF NOT EXISTS data_dictionary (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT NOT NULL,
    document_id     TEXT,
    dataset_name    TEXT NOT NULL,
    column_name     TEXT NOT NULL,
    data_type       TEXT NOT NULL,
    description     TEXT NOT NULL,
    source_field    TEXT NOT NULL,
    nullable        TEXT NOT NULL,
    example_value   TEXT,
    CONSTRAINT chk_dict_nullable CHECK (nullable IN ('true','false')),
    CONSTRAINT fk_dict_job FOREIGN KEY (job_id) REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_dict_doc FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
    CONSTRAINT uq_dict_column UNIQUE (job_id, dataset_name, column_name)
);
CREATE INDEX IF NOT EXISTS idx_dict_job_id ON data_dictionary(job_id);

-- ============================================================
-- 6. PROVENANCE: provenance
-- ============================================================
CREATE TABLE IF NOT EXISTS provenance (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id              TEXT NOT NULL,
    document_id         TEXT,
    dataset_name        TEXT NOT NULL,
    source_document     TEXT NOT NULL,
    source_section      TEXT NOT NULL,
    source_page         TEXT NOT NULL,
    extraction_method   TEXT NOT NULL,
    record_count        INTEGER NOT NULL CHECK (record_count >= 0),
    CONSTRAINT fk_prov_job FOREIGN KEY (job_id) REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_prov_doc FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
    CONSTRAINT uq_prov_job_dataset UNIQUE (job_id, dataset_name)
);
CREATE INDEX IF NOT EXISTS idx_prov_job_id ON provenance(job_id);

-- ============================================================
-- 7. REVIEW REQUIRED: review_required
-- ============================================================
CREATE TABLE IF NOT EXISTS review_required (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id            TEXT,
    document_id       TEXT,
    dataset_id        TEXT,
    original_value    TEXT NOT NULL,
    issue             TEXT NOT NULL,
    source_page       TEXT NOT NULL,
    reason            TEXT NOT NULL,
    agreement_score   NUMERIC(5,2),
    resolved          BOOLEAN NOT NULL DEFAULT 0,
    resolved_by       TEXT,
    resolved_at       TIMESTAMP,
    CONSTRAINT chk_agreement_score
        CHECK (agreement_score IS NULL OR (agreement_score >= 0 AND agreement_score <= 100)),
    CONSTRAINT fk_rr_job FOREIGN KEY (job_id) REFERENCES extraction_jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_rr_doc FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_rr_job_id ON review_required(job_id);
CREATE INDEX IF NOT EXISTS idx_rr_document_id ON review_required(document_id);
CREATE INDEX IF NOT EXISTS idx_rr_resolved ON review_required(resolved);
