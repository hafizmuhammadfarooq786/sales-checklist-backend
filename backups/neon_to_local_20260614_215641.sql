--
-- PostgreSQL database dump
--

\restrict XPmRcUiIWSZ0eKaoscgxGuRvBemsN8HcoV0QAglhQHiO9sFVbzQ4RP2sY2pQQTt

-- Dumped from database version 17.10 (98a80fa)
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_team_id_fkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_organization_id_fkey;
ALTER TABLE IF EXISTS ONLY public.transcripts DROP CONSTRAINT IF EXISTS transcripts_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.teams DROP CONSTRAINT IF EXISTS teams_organization_id_fkey;
ALTER TABLE IF EXISTS ONLY public.sessions DROP CONSTRAINT IF EXISTS sessions_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.session_responses DROP CONSTRAINT IF EXISTS session_responses_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.session_responses DROP CONSTRAINT IF EXISTS session_responses_item_id_fkey;
ALTER TABLE IF EXISTS ONLY public.session_response_analysis DROP CONSTRAINT IF EXISTS session_response_analysis_session_response_id_fkey;
ALTER TABLE IF EXISTS ONLY public.session_response_analysis DROP CONSTRAINT IF EXISTS session_response_analysis_behaviour_id_fkey;
ALTER TABLE IF EXISTS ONLY public.scoring_results DROP CONSTRAINT IF EXISTS scoring_results_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.score_history DROP CONSTRAINT IF EXISTS score_history_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.score_history DROP CONSTRAINT IF EXISTS score_history_scoring_result_id_fkey;
ALTER TABLE IF EXISTS ONLY public.score_history DROP CONSTRAINT IF EXISTS score_history_created_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.reports DROP CONSTRAINT IF EXISTS reports_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.organization_settings DROP CONSTRAINT IF EXISTS organization_settings_organization_id_fkey;
ALTER TABLE IF EXISTS ONLY public.organization_registration_requests DROP CONSTRAINT IF EXISTS organization_registration_requests_reviewed_by_fkey;
ALTER TABLE IF EXISTS ONLY public.organization_registration_requests DROP CONSTRAINT IF EXISTS organization_registration_requests_organization_id_fkey;
ALTER TABLE IF EXISTS ONLY public.manager_notes DROP CONSTRAINT IF EXISTS manager_notes_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.manager_notes DROP CONSTRAINT IF EXISTS manager_notes_manager_id_fkey;
ALTER TABLE IF EXISTS ONLY public.invitations DROP CONSTRAINT IF EXISTS invitations_team_id_fkey;
ALTER TABLE IF EXISTS ONLY public.invitations DROP CONSTRAINT IF EXISTS invitations_organization_id_fkey;
ALTER TABLE IF EXISTS ONLY public.invitations DROP CONSTRAINT IF EXISTS invitations_invited_by_fkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS fk_users_deleted_by;
ALTER TABLE IF EXISTS ONLY public.checklist_item_behaviours DROP CONSTRAINT IF EXISTS fk_checklist_item_behaviours_item_id;
ALTER TABLE IF EXISTS ONLY public.coaching_questions DROP CONSTRAINT IF EXISTS coaching_questions_item_id_fkey;
ALTER TABLE IF EXISTS ONLY public.coaching_feedback DROP CONSTRAINT IF EXISTS coaching_feedback_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checklist_items DROP CONSTRAINT IF EXISTS checklist_items_category_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checklist_item_notes DROP CONSTRAINT IF EXISTS checklist_item_notes_updated_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checklist_item_notes DROP CONSTRAINT IF EXISTS checklist_item_notes_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checklist_item_notes DROP CONSTRAINT IF EXISTS checklist_item_notes_previous_version_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checklist_item_notes DROP CONSTRAINT IF EXISTS checklist_item_notes_created_by_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.checklist_item_notes DROP CONSTRAINT IF EXISTS checklist_item_notes_checklist_item_id_fkey;
ALTER TABLE IF EXISTS ONLY public.audio_files DROP CONSTRAINT IF EXISTS audio_files_session_id_fkey;
DROP INDEX IF EXISTS public.uq_checklist_item_notes_active_per_item_opportunity;
DROP INDEX IF EXISTS public.ix_users_id;
DROP INDEX IF EXISTS public.ix_users_email;
DROP INDEX IF EXISTS public.ix_users_deleted_at;
DROP INDEX IF EXISTS public.ix_transcripts_id;
DROP INDEX IF EXISTS public.ix_teams_id;
DROP INDEX IF EXISTS public.ix_sessions_id;
DROP INDEX IF EXISTS public.ix_session_responses_id;
DROP INDEX IF EXISTS public.ix_session_response_analysis_session_response_id;
DROP INDEX IF EXISTS public.ix_session_response_analysis_id;
DROP INDEX IF EXISTS public.ix_session_response_analysis_evidence_found;
DROP INDEX IF EXISTS public.ix_session_response_analysis_behaviour_id;
DROP INDEX IF EXISTS public.ix_scoring_results_id;
DROP INDEX IF EXISTS public.ix_score_history_session_id;
DROP INDEX IF EXISTS public.ix_score_history_scoring_result_id;
DROP INDEX IF EXISTS public.ix_score_history_id;
DROP INDEX IF EXISTS public.ix_reports_id;
DROP INDEX IF EXISTS public.ix_organizations_id;
DROP INDEX IF EXISTS public.ix_organization_registration_requests_status;
DROP INDEX IF EXISTS public.ix_organization_registration_requests_id;
DROP INDEX IF EXISTS public.ix_organization_registration_requests_admin_email;
DROP INDEX IF EXISTS public.ix_manager_notes_session_id;
DROP INDEX IF EXISTS public.ix_manager_notes_note_type;
DROP INDEX IF EXISTS public.ix_manager_notes_manager_id;
DROP INDEX IF EXISTS public.ix_manager_notes_id;
DROP INDEX IF EXISTS public.ix_coaching_questions_id;
DROP INDEX IF EXISTS public.ix_coaching_feedback_id;
DROP INDEX IF EXISTS public.ix_checklist_items_id;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_version_lookup;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_updated_at;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_session_id;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_opportunity_key;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_opp_item;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_id;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_created_by_user_id;
DROP INDEX IF EXISTS public.ix_checklist_item_notes_checklist_item_id;
DROP INDEX IF EXISTS public.ix_checklist_item_behaviours_rowtype;
DROP INDEX IF EXISTS public.ix_checklist_item_behaviours_isactive;
DROP INDEX IF EXISTS public.ix_checklist_item_behaviours_id;
DROP INDEX IF EXISTS public.ix_checklist_item_behaviours_checklistitemname;
DROP INDEX IF EXISTS public.ix_checklist_categories_id;
DROP INDEX IF EXISTS public.ix_audio_files_id;
DROP INDEX IF EXISTS public.idx_users_team_role;
DROP INDEX IF EXISTS public.idx_users_team_active;
DROP INDEX IF EXISTS public.idx_users_org_active;
DROP INDEX IF EXISTS public.idx_sessions_user_updated_desc;
DROP INDEX IF EXISTS public.idx_sessions_user_updated;
DROP INDEX IF EXISTS public.idx_sessions_user_status;
DROP INDEX IF EXISTS public.idx_sessions_status_updated;
DROP INDEX IF EXISTS public.idx_sessions_mode;
DROP INDEX IF EXISTS public.idx_sessions_deal_stage;
DROP INDEX IF EXISTS public.idx_scoring_total_score;
DROP INDEX IF EXISTS public.idx_scoring_session_score;
DROP INDEX IF EXISTS public.idx_scoring_score_desc;
DROP INDEX IF EXISTS public.idx_scoring_risk_band;
DROP INDEX IF EXISTS public.idx_score_history_version;
DROP INDEX IF EXISTS public.idx_score_history_session_calc;
DROP INDEX IF EXISTS public.idx_responses_session_item;
DROP INDEX IF EXISTS public.idx_responses_session_answer;
DROP INDEX IF EXISTS public.idx_responses_item_answer;
DROP INDEX IF EXISTS public.idx_organization_settings_organization_id;
DROP INDEX IF EXISTS public.idx_manager_notes_created_at;
DROP INDEX IF EXISTS public.idx_invitations_token;
DROP INDEX IF EXISTS public.idx_invitations_organization_id;
DROP INDEX IF EXISTS public.idx_invitations_email;
DROP INDEX IF EXISTS public.idx_cib_checklist_item_id;
DROP INDEX IF EXISTS public.idx_checklist_items_category;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.transcripts DROP CONSTRAINT IF EXISTS transcripts_session_id_key;
ALTER TABLE IF EXISTS ONLY public.transcripts DROP CONSTRAINT IF EXISTS transcripts_pkey;
ALTER TABLE IF EXISTS ONLY public.teams DROP CONSTRAINT IF EXISTS teams_pkey;
ALTER TABLE IF EXISTS ONLY public.sessions DROP CONSTRAINT IF EXISTS sessions_pkey;
ALTER TABLE IF EXISTS ONLY public.session_responses DROP CONSTRAINT IF EXISTS session_responses_pkey;
ALTER TABLE IF EXISTS ONLY public.session_response_analysis DROP CONSTRAINT IF EXISTS session_response_analysis_pkey;
ALTER TABLE IF EXISTS ONLY public.scoring_results DROP CONSTRAINT IF EXISTS scoring_results_session_id_key;
ALTER TABLE IF EXISTS ONLY public.scoring_results DROP CONSTRAINT IF EXISTS scoring_results_pkey;
ALTER TABLE IF EXISTS ONLY public.score_history DROP CONSTRAINT IF EXISTS score_history_pkey;
ALTER TABLE IF EXISTS ONLY public.reports DROP CONSTRAINT IF EXISTS reports_session_id_key;
ALTER TABLE IF EXISTS ONLY public.reports DROP CONSTRAINT IF EXISTS reports_pkey;
ALTER TABLE IF EXISTS ONLY public.organizations DROP CONSTRAINT IF EXISTS organizations_pkey;
ALTER TABLE IF EXISTS ONLY public.organization_settings DROP CONSTRAINT IF EXISTS organization_settings_pkey;
ALTER TABLE IF EXISTS ONLY public.organization_settings DROP CONSTRAINT IF EXISTS organization_settings_organization_id_key;
ALTER TABLE IF EXISTS ONLY public.organization_registration_requests DROP CONSTRAINT IF EXISTS organization_registration_requests_pkey;
ALTER TABLE IF EXISTS ONLY public.manager_notes DROP CONSTRAINT IF EXISTS manager_notes_pkey;
ALTER TABLE IF EXISTS ONLY public.invitations DROP CONSTRAINT IF EXISTS invitations_token_key;
ALTER TABLE IF EXISTS ONLY public.invitations DROP CONSTRAINT IF EXISTS invitations_pkey;
ALTER TABLE IF EXISTS ONLY public.coaching_questions DROP CONSTRAINT IF EXISTS coaching_questions_pkey;
ALTER TABLE IF EXISTS ONLY public.coaching_feedback DROP CONSTRAINT IF EXISTS coaching_feedback_session_id_key;
ALTER TABLE IF EXISTS ONLY public.coaching_feedback DROP CONSTRAINT IF EXISTS coaching_feedback_pkey;
ALTER TABLE IF EXISTS ONLY public.checklist_items DROP CONSTRAINT IF EXISTS checklist_items_pkey;
ALTER TABLE IF EXISTS ONLY public.checklist_item_notes DROP CONSTRAINT IF EXISTS checklist_item_notes_pkey;
ALTER TABLE IF EXISTS ONLY public.checklist_item_behaviours DROP CONSTRAINT IF EXISTS checklist_item_behaviours_pkey;
ALTER TABLE IF EXISTS ONLY public.checklist_categories DROP CONSTRAINT IF EXISTS checklist_categories_pkey;
ALTER TABLE IF EXISTS ONLY public.checklist_categories DROP CONSTRAINT IF EXISTS checklist_categories_name_key;
ALTER TABLE IF EXISTS ONLY public.audio_files DROP CONSTRAINT IF EXISTS audio_files_session_id_key;
ALTER TABLE IF EXISTS ONLY public.audio_files DROP CONSTRAINT IF EXISTS audio_files_pkey;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.transcripts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.teams ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.sessions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.session_responses ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.session_response_analysis ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.scoring_results ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.score_history ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.reports ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.organizations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.organization_settings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.organization_registration_requests ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.manager_notes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.invitations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.coaching_questions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.coaching_feedback ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.checklist_items ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.checklist_item_notes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.checklist_item_behaviours ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.checklist_categories ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.audio_files ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
DROP SEQUENCE IF EXISTS public.transcripts_id_seq;
DROP TABLE IF EXISTS public.transcripts;
DROP SEQUENCE IF EXISTS public.teams_id_seq;
DROP TABLE IF EXISTS public.teams;
DROP SEQUENCE IF EXISTS public.sessions_id_seq;
DROP TABLE IF EXISTS public.sessions;
DROP SEQUENCE IF EXISTS public.session_responses_id_seq;
DROP TABLE IF EXISTS public.session_responses;
DROP SEQUENCE IF EXISTS public.session_response_analysis_id_seq;
DROP TABLE IF EXISTS public.session_response_analysis;
DROP SEQUENCE IF EXISTS public.scoring_results_id_seq;
DROP TABLE IF EXISTS public.scoring_results;
DROP SEQUENCE IF EXISTS public.score_history_id_seq;
DROP TABLE IF EXISTS public.score_history;
DROP SEQUENCE IF EXISTS public.reports_id_seq;
DROP TABLE IF EXISTS public.reports;
DROP SEQUENCE IF EXISTS public.organizations_id_seq;
DROP TABLE IF EXISTS public.organizations;
DROP SEQUENCE IF EXISTS public.organization_settings_id_seq;
DROP TABLE IF EXISTS public.organization_settings;
DROP SEQUENCE IF EXISTS public.organization_registration_requests_id_seq;
DROP TABLE IF EXISTS public.organization_registration_requests;
DROP SEQUENCE IF EXISTS public.manager_notes_id_seq;
DROP TABLE IF EXISTS public.manager_notes;
DROP SEQUENCE IF EXISTS public.invitations_id_seq;
DROP TABLE IF EXISTS public.invitations;
DROP SEQUENCE IF EXISTS public.coaching_questions_id_seq;
DROP TABLE IF EXISTS public.coaching_questions;
DROP SEQUENCE IF EXISTS public.coaching_feedback_id_seq;
DROP TABLE IF EXISTS public.coaching_feedback;
DROP SEQUENCE IF EXISTS public.checklist_items_id_seq;
DROP TABLE IF EXISTS public.checklist_items;
DROP SEQUENCE IF EXISTS public.checklist_item_notes_id_seq;
DROP TABLE IF EXISTS public.checklist_item_notes;
DROP SEQUENCE IF EXISTS public.checklist_item_behaviours_id_seq;
DROP TABLE IF EXISTS public.checklist_item_behaviours;
DROP SEQUENCE IF EXISTS public.checklist_categories_id_seq;
DROP TABLE IF EXISTS public.checklist_categories;
DROP SEQUENCE IF EXISTS public.audio_files_id_seq;
DROP TABLE IF EXISTS public.audio_files;
DROP TABLE IF EXISTS public.alembic_version;
DROP TYPE IF EXISTS public.userrole;
DROP TYPE IF EXISTS public.sessionstatus;
DROP TYPE IF EXISTS public.sessionmode;
DROP TYPE IF EXISTS public.riskband;
DROP TYPE IF EXISTS public.organizationregistrationstatus;
DROP TYPE IF EXISTS public.notetype;
--
-- Name: notetype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notetype AS ENUM (
    'TEXT',
    'AUDIO'
);


--
-- Name: organizationregistrationstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.organizationregistrationstatus AS ENUM (
    'pending',
    'approved',
    'rejected'
);


--
-- Name: riskband; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.riskband AS ENUM (
    'GREEN',
    'YELLOW',
    'RED'
);


--
-- Name: sessionmode; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.sessionmode AS ENUM (
    'AUDIO',
    'MANUAL'
);


--
-- Name: sessionstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.sessionstatus AS ENUM (
    'DRAFT',
    'UPLOADING',
    'PROCESSING',
    'ANALYZING',
    'SCORING',
    'COMPLETED',
    'FAILED',
    'pending_review',
    'PENDING_REVIEW'
);


--
-- Name: userrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'MANAGER',
    'REP',
    'system_admin',
    'SYSTEM_ADMIN',
    'EXECUTIVE'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: audio_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audio_files (
    id integer NOT NULL,
    session_id integer NOT NULL,
    filename character varying(500) NOT NULL,
    file_path character varying(1000) NOT NULL,
    storage_type character varying(50),
    file_size integer NOT NULL,
    mime_type character varying(100) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: audio_files_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audio_files_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audio_files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audio_files_id_seq OWNED BY public.audio_files.id;


--
-- Name: checklist_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checklist_categories (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    "order" integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: checklist_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.checklist_categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: checklist_categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.checklist_categories_id_seq OWNED BY public.checklist_categories.id;


--
-- Name: checklist_item_behaviours; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checklist_item_behaviours (
    id integer NOT NULL,
    checklistitemname character varying(255) NOT NULL,
    rowtype character varying(20) NOT NULL,
    coachingarea character varying(100),
    "order" integer NOT NULL,
    question text,
    behaviour text,
    keyreminder text,
    isactive boolean NOT NULL,
    createdat timestamp without time zone DEFAULT now() NOT NULL,
    updatedat timestamp without time zone DEFAULT now() NOT NULL,
    checklist_item_id integer NOT NULL
);


--
-- Name: checklist_item_behaviours_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.checklist_item_behaviours_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: checklist_item_behaviours_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.checklist_item_behaviours_id_seq OWNED BY public.checklist_item_behaviours.id;


--
-- Name: checklist_item_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checklist_item_notes (
    id integer NOT NULL,
    checklist_item_id integer NOT NULL,
    session_id integer,
    customer_name character varying(255) NOT NULL,
    opportunity_name character varying(255) NOT NULL,
    opportunity_key character varying(64) NOT NULL,
    note_text text,
    decision_influencers jsonb,
    created_by_user_id integer,
    updated_by_user_id integer,
    is_active boolean NOT NULL,
    version integer NOT NULL,
    previous_version_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    structured_content jsonb
);


--
-- Name: checklist_item_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.checklist_item_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: checklist_item_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.checklist_item_notes_id_seq OWNED BY public.checklist_item_notes.id;


--
-- Name: checklist_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.checklist_items (
    id integer NOT NULL,
    category_id integer NOT NULL,
    title character varying(500) NOT NULL,
    definition text NOT NULL,
    "order" integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: checklist_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.checklist_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: checklist_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.checklist_items_id_seq OWNED BY public.checklist_items.id;


--
-- Name: coaching_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coaching_feedback (
    id integer NOT NULL,
    session_id integer NOT NULL,
    feedback_text text NOT NULL,
    strengths json,
    improvement_areas json,
    action_items json,
    generated_at timestamp without time zone,
    openai_request_id character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: coaching_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.coaching_feedback_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: coaching_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.coaching_feedback_id_seq OWNED BY public.coaching_feedback.id;


--
-- Name: coaching_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coaching_questions (
    id integer NOT NULL,
    item_id integer NOT NULL,
    section character varying(255) NOT NULL,
    question text NOT NULL,
    "order" integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: coaching_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.coaching_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: coaching_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.coaching_questions_id_seq OWNED BY public.coaching_questions.id;


--
-- Name: invitations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invitations (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    organization_id integer NOT NULL,
    team_id integer,
    role character varying(50) NOT NULL,
    token character varying(255) NOT NULL,
    invited_by integer,
    expires_at timestamp without time zone NOT NULL,
    accepted_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: invitations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.invitations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: invitations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.invitations_id_seq OWNED BY public.invitations.id;


--
-- Name: manager_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.manager_notes (
    id integer NOT NULL,
    session_id integer NOT NULL,
    manager_id integer NOT NULL,
    note_text text,
    is_edited boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    note_type character varying(10) DEFAULT 'text'::character varying NOT NULL,
    audio_s3_bucket character varying(255),
    audio_s3_key character varying(512),
    audio_duration integer,
    audio_file_size integer
);


--
-- Name: manager_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.manager_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: manager_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.manager_notes_id_seq OWNED BY public.manager_notes.id;


--
-- Name: organization_registration_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_registration_requests (
    id integer NOT NULL,
    status public.organizationregistrationstatus DEFAULT 'pending'::public.organizationregistrationstatus NOT NULL,
    company_name character varying(255) NOT NULL,
    industry character varying(100) NOT NULL,
    logo_url text,
    admin_first_name character varying(100) NOT NULL,
    admin_last_name character varying(100) NOT NULL,
    admin_email character varying(255) NOT NULL,
    admin_direct_dial character varying(50) NOT NULL,
    admin_cell_phone character varying(50),
    additional_users jsonb DEFAULT '[]'::jsonb NOT NULL,
    organization_id integer,
    reviewed_by integer,
    reviewed_at timestamp without time zone,
    rejection_reason text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: organization_registration_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.organization_registration_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: organization_registration_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.organization_registration_requests_id_seq OWNED BY public.organization_registration_requests.id;


--
-- Name: organization_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_settings (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    allow_self_registration boolean DEFAULT false NOT NULL,
    default_role character varying(50) DEFAULT 'rep'::character varying NOT NULL,
    logo_url text,
    primary_color character varying(7),
    settings jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    executive_sponsor_name character varying(255),
    executive_sponsor_email character varying(255),
    executive_sponsor_direct_dial character varying(50),
    executive_sponsor_cell_phone character varying(50)
);


--
-- Name: organization_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.organization_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: organization_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.organization_settings_id_seq OWNED BY public.organization_settings.id;


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    industry character varying(100)
);


--
-- Name: organizations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.organizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: organizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.organizations_id_seq OWNED BY public.organizations.id;


--
-- Name: reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reports (
    id integer NOT NULL,
    session_id integer NOT NULL,
    pdf_s3_bucket character varying(255),
    pdf_s3_key character varying(500),
    pdf_file_size integer,
    generated_at timestamp without time zone,
    is_generated boolean,
    emailed_at timestamp without time zone,
    emailed_to character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reports_id_seq OWNED BY public.reports.id;


--
-- Name: score_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.score_history (
    id integer NOT NULL,
    session_id integer NOT NULL,
    scoring_result_id integer,
    total_score double precision NOT NULL,
    risk_band public.riskband NOT NULL,
    items_validated integer NOT NULL,
    items_total integer NOT NULL,
    calculated_at timestamp without time zone NOT NULL,
    score_change double precision,
    trigger_event character varying(100),
    created_by_user_id integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    version_number integer NOT NULL,
    changes_count integer,
    responses_snapshot json NOT NULL
);


--
-- Name: score_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.score_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: score_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.score_history_id_seq OWNED BY public.score_history.id;


--
-- Name: scoring_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scoring_results (
    id integer NOT NULL,
    session_id integer NOT NULL,
    total_score double precision NOT NULL,
    risk_band public.riskband NOT NULL,
    category_scores json,
    top_strengths json,
    top_gaps json,
    items_validated integer NOT NULL,
    items_total integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: scoring_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scoring_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scoring_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scoring_results_id_seq OWNED BY public.scoring_results.id;


--
-- Name: session_response_analysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_response_analysis (
    id integer NOT NULL,
    session_response_id integer NOT NULL,
    behaviour_id integer NOT NULL,
    evidence_found boolean NOT NULL,
    evidence_text text,
    ai_reasoning text,
    confidence_score double precision,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: session_response_analysis_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.session_response_analysis_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: session_response_analysis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.session_response_analysis_id_seq OWNED BY public.session_response_analysis.id;


--
-- Name: session_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_responses (
    id integer NOT NULL,
    session_id integer NOT NULL,
    item_id integer NOT NULL,
    ai_reasoning text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    ai_answer boolean NOT NULL,
    user_answer boolean,
    was_changed boolean,
    score integer NOT NULL
);


--
-- Name: session_responses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.session_responses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: session_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.session_responses_id_seq OWNED BY public.session_responses.id;


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sessions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    customer_name character varying(255) NOT NULL,
    opportunity_name character varying(255) NOT NULL,
    decision_influencer character varying(255),
    status public.sessionstatus NOT NULL,
    submitted_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    session_mode character varying(20) DEFAULT 'audio'::character varying NOT NULL,
    deal_stage character varying(64)
);


--
-- Name: sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sessions_id_seq OWNED BY public.sessions.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    organization_id integer NOT NULL,
    name character varying(255) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: transcripts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transcripts (
    id integer NOT NULL,
    session_id integer NOT NULL,
    text text NOT NULL,
    language character varying(10),
    duration double precision,
    words_count integer,
    transcribed_at timestamp without time zone,
    processing_time double precision,
    openai_request_id character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: transcripts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.transcripts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: transcripts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.transcripts_id_seq OWNED BY public.transcripts.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    first_name character varying(100),
    last_name character varying(100),
    role public.userrole NOT NULL,
    organization_id integer,
    team_id integer,
    is_active boolean NOT NULL,
    last_login timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_verified boolean NOT NULL,
    failed_login_attempts integer NOT NULL,
    locked_until timestamp without time zone,
    password_reset_token character varying(255),
    password_reset_expires timestamp without time zone,
    email_verification_token character varying(255),
    email_verification_expires timestamp without time zone,
    deleted_at timestamp without time zone,
    deleted_by integer,
    must_change_password boolean NOT NULL,
    direct_dial character varying(50),
    cell_phone character varying(50),
    job_title character varying(150)
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: audio_files id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audio_files ALTER COLUMN id SET DEFAULT nextval('public.audio_files_id_seq'::regclass);


--
-- Name: checklist_categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_categories ALTER COLUMN id SET DEFAULT nextval('public.checklist_categories_id_seq'::regclass);


--
-- Name: checklist_item_behaviours id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_behaviours ALTER COLUMN id SET DEFAULT nextval('public.checklist_item_behaviours_id_seq'::regclass);


--
-- Name: checklist_item_notes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_notes ALTER COLUMN id SET DEFAULT nextval('public.checklist_item_notes_id_seq'::regclass);


--
-- Name: checklist_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_items ALTER COLUMN id SET DEFAULT nextval('public.checklist_items_id_seq'::regclass);


--
-- Name: coaching_feedback id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaching_feedback ALTER COLUMN id SET DEFAULT nextval('public.coaching_feedback_id_seq'::regclass);


--
-- Name: coaching_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaching_questions ALTER COLUMN id SET DEFAULT nextval('public.coaching_questions_id_seq'::regclass);


--
-- Name: invitations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitations ALTER COLUMN id SET DEFAULT nextval('public.invitations_id_seq'::regclass);


--
-- Name: manager_notes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.manager_notes ALTER COLUMN id SET DEFAULT nextval('public.manager_notes_id_seq'::regclass);


--
-- Name: organization_registration_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_registration_requests ALTER COLUMN id SET DEFAULT nextval('public.organization_registration_requests_id_seq'::regclass);


--
-- Name: organization_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_settings ALTER COLUMN id SET DEFAULT nextval('public.organization_settings_id_seq'::regclass);


--
-- Name: organizations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations ALTER COLUMN id SET DEFAULT nextval('public.organizations_id_seq'::regclass);


--
-- Name: reports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports ALTER COLUMN id SET DEFAULT nextval('public.reports_id_seq'::regclass);


--
-- Name: score_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_history ALTER COLUMN id SET DEFAULT nextval('public.score_history_id_seq'::regclass);


--
-- Name: scoring_results id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scoring_results ALTER COLUMN id SET DEFAULT nextval('public.scoring_results_id_seq'::regclass);


--
-- Name: session_response_analysis id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_response_analysis ALTER COLUMN id SET DEFAULT nextval('public.session_response_analysis_id_seq'::regclass);


--
-- Name: session_responses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_responses ALTER COLUMN id SET DEFAULT nextval('public.session_responses_id_seq'::regclass);


--
-- Name: sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions ALTER COLUMN id SET DEFAULT nextval('public.sessions_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Name: transcripts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transcripts ALTER COLUMN id SET DEFAULT nextval('public.transcripts_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
e5f6a7b8c9d0
\.


--
-- Data for Name: audio_files; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audio_files (id, session_id, filename, file_path, storage_type, file_size, mime_type, created_at, updated_at) FROM stdin;
52	89	89_7455fdc14e6a4281a61d0ce9f5eee0f0.mp3	https://sales-checklist.s3.us-east-2.amazonaws.com/audio/14/89/89_7455fdc14e6a4281a61d0ce9f5eee0f0.mp3	s3	11346782	audio/mpeg	2026-04-01 15:29:31.431865	2026-04-01 15:29:31.431874
53	90	90_a1e7d1f56b534f19afefb8fa8b450235.webm	https://sales-checklist.s3.us-east-2.amazonaws.com/audio/14/90/90_a1e7d1f56b534f19afefb8fa8b450235.webm	s3	390793	audio/webm	2026-04-01 15:39:34.443558	2026-04-01 15:39:34.443567
54	93	93_49a03804b2804928ac2254bb8e3ddd39.webm	https://sales-checklist.s3.us-east-2.amazonaws.com/audio/14/93/93_49a03804b2804928ac2254bb8e3ddd39.webm	s3	389827	audio/webm	2026-04-01 15:58:37.920817	2026-04-01 15:58:37.920825
55	94	94_b4cab01168004cb3b6f6e687e4636cba.webm	https://sales-checklist.s3.us-east-2.amazonaws.com/audio/14/94/94_b4cab01168004cb3b6f6e687e4636cba.webm	s3	326973	audio/webm	2026-04-01 16:30:36.90055	2026-04-01 16:30:36.900559
56	95	95_d8cf3993c53447829a570085b30eac7d.webm	https://sales-checklist.s3.us-east-2.amazonaws.com/audio/14/95/95_d8cf3993c53447829a570085b30eac7d.webm	s3	378219	audio/webm	2026-04-01 18:43:55.134731	2026-04-01 18:43:55.134735
58	96	96_5ad3a0df3d2740159e92f0b586958b47.webm	https://sales-checklist.s3.us-east-2.amazonaws.com/audio/14/96/96_5ad3a0df3d2740159e92f0b586958b47.webm	s3	427532	audio/webm	2026-04-06 10:00:22.843912	2026-04-06 10:00:22.843915
\.


--
-- Data for Name: checklist_categories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.checklist_categories (id, name, description, "order", is_active, created_at, updated_at) FROM stdin;
52	Sales Checklist	10 essential checklist items for effective sales process validation	1	t	2025-12-03 15:18:38.49821	2025-12-03 15:18:38.49822
\.


--
-- Data for Name: checklist_item_behaviours; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.checklist_item_behaviours (id, checklistitemname, rowtype, coachingarea, "order", question, behaviour, keyreminder, isactive, createdat, updatedat, checklist_item_id) FROM stdin;
22	Trigger Priority	Question	Finalizer Validation	5	What proof do you have (not assumptions)?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
48	Finalizer	Behavior		0				t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
84	Customer Fit	Behavior		0		Ensures that the customer is a good Fit before investing significant selling time and company resources. Additionally, continually validates that the client remains a good fit throughout the sales cycle.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
85	Customer Fit	Question	Leadership Access	1	What clear evidence do we have that senior leadership is accessible, engaged, and taking ownership of the problem?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
86	Customer Fit	Question	Brand & Value Appreciation	2	What proof do we have that they genuinely understand and value our differentiation?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
87	Customer Fit	Question	Brand & Value Appreciation	3	“We like your product” without willingness to invest ≠ true value appreciation. What evidence do we have of real value alignment?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
88	Customer Fit	Question	Influencer Support	4	Which Decision Influencers have demonstrated real appreciation for our brand, expertise, and value?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
89	Customer Fit	Question	Influencer Support	5	Are there signs that purchasing is attempting to commoditize the evaluation? If so, what does that signal about Fit?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
90	Customer Fit	Question	Communication Style	6	How have they demonstrated openness, honesty, responsiveness, and transparency in our interactions?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
91	Customer Fit	Question	Fit Validation	7	Which Fit criteria have been explicitly validated, and which remain unvalidated?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
92	Customer Fit	Question	Fit Validation	8	How do you know? What conversations or evidence confirm this?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
93	Customer Fit	Question	Opportunity Size	9	What is the estimated size of the opportunity, and how confident are we in that estimate?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
94	Customer Fit	Question	Planning Forward	10	How does our current Fit assessment shape the next steps, engagement strategy, and resource allocation?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
95	Customer Fit	Question	Stay or Disengage	11	If this is not a strong Fit, is there a compelling reason to remain engaged?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
96	Customer Fit	Question	Stay or Disengage	12	If not, what exit criteria would signal it's time to disengage professionally?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
97	Customer Fit	Question	Action Plan if Gaps Exist	13	If Solution Fit is not fully validated, who do you need to speak with next to confirm it?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
98	Customer Fit	Question	Action Plan if Gaps Exist	14	What specific actions will you take to close remaining gaps, resolve doubts, or validate missing criteria?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
99	Customer Fit	Reminder		999			Validating Customer Fit early is essential. It prevents wasted effort, protects pipeline quality, and significantly increases win rates.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	134
113	Trigger Event	Behavior		0		Clearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
114	Trigger Event	Question	Motivation for Change	1	What is driving the Decision Influencer to act now, and what measurable outcomes are they seeking (cost, time, risk, performance)?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
115	Trigger Event	Question	True Trigger Event	2	Are you addressing the real Trigger Event or just a symptom?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
116	Trigger Event	Question	True Trigger Event	3	What specific incident, failure, or change created urgency — and what is the root cause?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
117	Trigger Event	Question	Impact & Measurement	4	How will they define and measure success?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
118	Trigger Event	Question	Impact & Measurement	5	What did they explicitly confirm, clarify, or deny when you validated the Trigger Event?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
119	Trigger Event	Question	Trigger Source	6	Was the Trigger self-identified or externally driven (audit, leadership, competitor, regulation, market change)?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
120	Trigger Event	Question	Trigger Source	7	Did you uncover a deeper, previously unspoken issue?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
121	Trigger Event	Question	Stakeholder Impact	8	Who benefits most if this is solved, and who is most impacted if nothing changes?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
122	Trigger Event	Question	Next Actions	9	If the Trigger Event is unclear, who will you ask next, what will you ask, and how will you leverage a Mentor or internal advocate?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
123	Trigger Event	Reminder		999			Keep it simple: What do they want to fix, accomplish, or avoid — and why now? If you can answer that clearly and validate it across stakeholders, you have real Motivation for Change.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	135
72	Sales Target	Behavior		0		Understands — from the customer’s perspective — what they are planning to buy, how much, why, when, and how the decision will be made.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
73	Sales Target	Question	Decision Authority & Process	1	Who is involved, who is the true Finalizer, and what proof confirms decision authority?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
74	Sales Target	Question	Decision Authority & Process	2	Have you engaged them? If not, what is your access plan?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
75	Sales Target	Question	Timing, Quantity & Urgency	3	How much are they buying and by when?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
76	Sales Target	Question	Timing, Quantity & Urgency	4	Why that timing, what happens if it slips, and is urgency real or assumed?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
77	Sales Target	Question	Solution Fit & Evaluation	5	Does our solution match what they intend to buy?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
78	Sales Target	Question	Solution Fit & Evaluation	6	How will each influencer evaluate options and define success?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
79	Sales Target	Question	Funding & Risk	7	Is funding confirmed or assumed?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
80	Sales Target	Question	Funding & Risk	8	What internal risks — political, financial, operational — could derail the deal?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
81	Sales Target	Question	Expansion & Next Actions	9	Are add-on or expansion opportunities present?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
82	Sales Target	Question	Expansion & Next Actions	10	What is still unknown, and who will you ask next to resolve it?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
83	Sales Target	Reminder		999			High-performing salespeople validate timing early and often — and they never assume urgency without proof.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	136
30	Decision Influencers — Specifier, Utilizer, Finalizer	Behavior		0		Understands that every sale involves three types of Decision Influencers — Specifiers, Utilizers, Finalizers — and tailors conversations based on what each values.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
31	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Specifier Verification	1	Who have you identified as Specifiers?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
32	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Specifier Verification	2	How did you verify they truly play this role?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
33	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Specifier Verification	3	Are any external consultants/advisors influencing specifications?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
34	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Specifier Verification	4	What specifications are they using, and who created them?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
35	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Specifier Verification	5	What matters most to them in evaluating options?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
36	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Utilizer Verification	6	Who have you identified as Utilizers?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
37	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Utilizer Verification	7	How did you confirm they are Utilizers?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
38	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Utilizer Verification	8	What do they care about most (ease of use, reliability, safety, efficiency)?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
39	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Utilizer Verification	9	How will they be impacted by the final decision?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
40	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Finalizer Verification	10	Who is the Finalizer? What proof confirms they have final authority?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
41	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Finalizer Verification	11	Have you engaged them directly? If not, what is your access plan and timeline?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
42	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Finalizer Verification	12	Once they say “yes,” what happens next? Is there another approval gate?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
43	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Finalizer Verification	13	What does the Finalizer personally value most? How is your message aligned to that?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
44	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Finalizer Verification	14	Who confirmed timing, scope, and purchase priorities?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
45	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Finalizer Verification	15	Who can credibly influence or introduce the Finalizer—and what have they done?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
46	Decision Influencers — Specifier, Utilizer, Finalizer	Question	Finalizer Verification	16	What is still unclear, and who will you ask next to resolve it?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
47	Decision Influencers — Specifier, Utilizer, Finalizer	Reminder		999			Specifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	138
139	Decision Influencer — Mentor	Behavior		0		Develops true Mentors, validates their commitment through actions, and leverages them strategically throughout the pursuit.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
140	Decision Influencer — Mentor	Question	Developing a Mentor	1	Do you have a Mentor? If not, what does that signal about deal viability?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
141	Decision Influencer — Mentor	Question	Developing a Mentor	2	Who has the most to gain if this succeeds — and the most to lose if it fails?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
142	Decision Influencer — Mentor	Question	Developing a Mentor	3	Who else shows strong belief in our solution?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
143	Decision Influencer — Mentor	Question	Developing a Mentor	4	If you had to name a Mentor today, who is the strongest candidate — and why?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
144	Decision Influencer — Mentor	Question	Developing a Mentor	5	If your current Mentor disappeared, who would replace them?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
145	Decision Influencer — Mentor	Question	Developing a Mentor	6	Who fits the Mentor profile but remains hesitant — and what’s holding them back?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
146	Decision Influencer — Mentor	Question	Validating a Mentor	7	Who is our Mentor, and what specific actions prove their commitment?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
147	Decision Influencer — Mentor	Question	Validating a Mentor	8	Exclusivity test: Would they take the same actions for a competitor? If yes, they are not a Mentor.			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
148	Decision Influencer — Mentor	Question	Validating a Mentor	9	What have they done recently to advance or protect our position?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
149	Decision Influencer — Mentor	Question	Validating a Mentor	10	How have they helped influence other Decision Influencers or access the Finalizer?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
150	Decision Influencer — Mentor	Question	Validating a Mentor	11	What strategic shifts resulted directly from their insights?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
151	Decision Influencer — Mentor	Question	Validating a Mentor	12	What non-public information have they shared that competitors would not receive?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
152	Decision Influencer — Mentor	Question	Validating a Mentor	13	Who is mentoring the competition, and how will you confirm it?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
153	Decision Influencer — Mentor	Question	Validating a Mentor	14	For complex deals, who is the secondary (1.5) Mentor?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
154	Decision Influencer — Mentor	Question	Validating a Mentor	15	If Mentor status is uncertain, what is your next step to confirm or disqualify it?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
155	Decision Influencer — Mentor	Question	Leveraging a Mentor	16	How will you explicitly ask for mentoring or coaching?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
156	Decision Influencer — Mentor	Question	Leveraging a Mentor	17	What risks or unresolved issues could derail this deal?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
157	Decision Influencer — Mentor	Question	Leveraging a Mentor	18	Where does this project rank among the Finalizer’s priorities?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
158	Decision Influencer — Mentor	Question	Leveraging a Mentor	19	What is the single biggest threat to success?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
159	Decision Influencer — Mentor	Question	Leveraging a Mentor	20	Who wins most if we succeed — and who loses if we fail?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
160	Decision Influencer — Mentor	Question	Leveraging a Mentor	21	What alternatives are being considered, and by whom?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
161	Decision Influencer — Mentor	Question	Leveraging a Mentor	22	How else can your Mentor help strengthen or secure the outcome?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
162	Decision Influencer — Mentor	Question	Leveraging a Mentor	23	If no Mentor exists, who can provide credible internal coaching?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
163	Decision Influencer — Mentor	Reminder		999			A Decision Influencer is a Mentor only if all three are true: You have credibility with them • They influence other Decision Influencers • They want only your solution.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	139
17	Trigger Priority	Behavior		0		Understands that even if a company is buying (RFQ/RFP), not every Decision Influencer feels the same urgency — and therefore evaluates priority individually, not collectively.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
18	Trigger Priority	Question	Priority Across Decision Influencers	1	Which Decision Influencers consider solving the Trigger Event a high priority?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
19	Trigger Priority	Question	Priority Across Decision Influencers	2	Which do not — and what roles do they play?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
20	Trigger Priority	Question	Priority Across Decision Influencers	3	Why do some influencers see it as lower priority?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
21	Trigger Priority	Question	Finalizer Validation	4	How have you confirmed that this project is a priority for the Finalizer?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
23	Trigger Priority	Question	Competing Projects & Shifting Priorities	6	What other initiatives could outrank or delay this one?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
24	Trigger Priority	Question	Competing Projects & Shifting Priorities	7	How can we increase the perceived urgency and importance of our project?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
25	Trigger Priority	Question	Mentor Leverage	8	How has your Mentor helped validate priority levels across stakeholders?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
26	Trigger Priority	Question	Mentor Leverage	9	What insights have they shared about internal urgency or risk?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
27	Trigger Priority	Question	Action Plan if Gaps Exist	10	If Trigger Priority is unclear, whom will you ask — and why them?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
28	Trigger Priority	Question	Action Plan if Gaps Exist	11	What specific questions will you use to uncover real urgency?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
29	Trigger Priority	Reminder		999			A company may be “buying,” but not every Decision Influencer feels urgency. Your success depends on identifying, validating, and elevating priority at the individual level, not assuming company-wide alignment.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	140
100	Individual Impact — What's in it for Me?	Behavior		0		Understands that people buy, companies do not and seeks to link their product or service to what is important to each individual key Decision Influencer in a manner that the competition cannot.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
101	Individual Impact — What's in it for Me?	Question	Linking Solution to Individual Impact	1	When we deliver the results the Decision Influencer is seeking, how are they personally impacted?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
102	Individual Impact — What's in it for Me?	Question	Linking Solution to Individual Impact	2	Do they fully understand this impact?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
103	Individual Impact — What's in it for Me?	Question	Linking Solution to Individual Impact	3	How clearly do they see the connection between our solution and their personal success?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
104	Individual Impact — What's in it for Me?	Question	Competitive Differentiation	4	Can the competition deliver the same personal impact?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
105	Individual Impact — What's in it for Me?	Question	Competitive Differentiation	5	What about our solution uniquely strengthens the WIIFM for key Decision Influencers?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
106	Individual Impact — What's in it for Me?	Question	Organizational Dynamics	6	If our solution is implemented, who within their organization would be positively impacted, and how can we leverage their support?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
107	Individual Impact — What's in it for Me?	Question	Organizational Dynamics	7	Who might be negatively impacted, and how can we proactively address their concerns?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
108	Individual Impact — What's in it for Me?	Question	Finalizer-Specific Impact	8	Have we identified the WIIFM for the Finalizer?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
109	Individual Impact — What's in it for Me?	Question	Finalizer-Specific Impact	9	How can we use our Mentor to uncover or confirm the Finalizer’s personal motivations?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
110	Individual Impact — What's in it for Me?	Question	Action Planning	10	If you don’t yet know the Individual Impact, whom will you ask?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
111	Individual Impact — What's in it for Me?	Question	Action Planning	11	What specific questions will you use to uncover this critical information?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
112	Individual Impact — What's in it for Me?	Reminder		999			Winning sales isn’t just about proving value — it’s about making each Decision Influencer feel that the success of the project directly benefits them in ways they personally care about.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	143
49	Finalizer	Question	Finalizer – Core Questions	1	Who has the final authority to say “yes” or “no”?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
50	Finalizer	Question	Finalizer – Core Questions	2	What proof confirms they hold this authority?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
51	Finalizer	Question	Finalizer – Core Questions	3	Have you engaged them? If not, what is your plan?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
52	Finalizer	Question	Finalizer – Core Questions	4	What happens after the Finalizer approves — does the order move immediately?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
53	Finalizer	Question	Finalizer – Core Questions	5	What does the Finalizer personally value (cost, outcomes, risk, reliability)?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
54	Finalizer	Question	Finalizer – Core Questions	6	How are you aligning your message with what they value most?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
55	Finalizer	Question	Finalizer – Core Questions	7	Who inside the organization can help you access or influence the Finalizer?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
56	Finalizer	Question	Finalizer – Core Questions	8	Who is the Finalizer — and how have you confirmed it?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
57	Finalizer	Question	Finalizer – Core Questions	9	What evidence shows they have final authority?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
58	Finalizer	Question	Finalizer – Core Questions	10	Have you spoken with them? If not, what's your plan and timeline?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
59	Finalizer	Question	Finalizer – Core Questions	11	What do they care about most — and how have you positioned around that?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
60	Finalizer	Question	Finalizer – Core Questions	12	Who confirmed timing, quantity, and purchase priorities?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
61	Finalizer	Question	Finalizer – Core Questions	13	If unclear, who will you ask — and how will you ask?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
62	Finalizer	Question	Finalizer – Core Questions	14	Once they approve, what happens next — does the order move immediately?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
63	Finalizer	Question	Finalizer – Core Questions	15	What does the Finalizer personally value most (cost, outcomes, risk, reliability)?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
64	Finalizer	Question	Finalizer – Core Questions	16	How are you aligning your message to those priorities?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
65	Finalizer	Question	Finalizer – Core Questions	17	Who inside the organization can help you access or influence the Finalizer?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
66	Finalizer	Question	Finalizer – Coaching Prompts	18	How did you confirm the Finalizer’s authority?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
67	Finalizer	Question	Finalizer – Coaching Prompts	19	What evidence proves they control timing, quantity, and approval?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
68	Finalizer	Question	Finalizer – Coaching Prompts	20	If you haven’t spoken with them, why not — and what’s your plan?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
69	Finalizer	Question	Finalizer – Coaching Prompts	21	How have you positioned our solution around what matters most to them?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
70	Finalizer	Question	Finalizer – Coaching Prompts	22	If anything is unclear, who will you ask — and exactly what will you ask?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
71	Finalizer	Reminder		999				t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	137
1	Alternatives	Behavior		0		Systematically identifies all alternatives — competitors, internal options, and “do nothing” — understands who supports each, and uses that insight to differentiate and reduce risk. Reminder: Competition is anything that can keep us from getting paid.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
2	Alternatives	Question	Alternative Identification	1	What alternatives is the customer considering (competitors, internal options, or doing nothing)?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
3	Alternatives	Question	Alternative Identification	2	How does the customer perceive each alternative relative to us?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
4	Alternatives	Question	Alternative Identification	3	Is “do nothing” a viable option for them — and what is the real cost of inaction?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
5	Alternatives	Question	Stakeholder Support	4	Which Decision Influencers support each alternative?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
6	Alternatives	Question	Stakeholder Support	5	Why are they advocating for that option?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
7	Alternatives	Question	Internal Alternatives	6	Are internal options (status quo, reallocation, internal build) being considered?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
8	Alternatives	Question	Internal Alternatives	7	How do politics, budget, or resources affect these choices?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
9	Alternatives	Question	Competitive Insight	8	Which competitors are involved?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
10	Alternatives	Question	Competitive Insight	9	From the customer’s perspective, what are their strengths and weaknesses?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
11	Alternatives	Question	Competitive Insight	10	Where do they see our strengths — and perceived gaps?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
12	Alternatives	Question	Differentiation Strategy	11	How are you clearly differentiating our solution from every alternative?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
13	Alternatives	Question	Differentiation Strategy	12	What proof points (results, stories, evidence) reinforce our position?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
14	Alternatives	Question	Mentor Leverage	13	How has your Mentor helped uncover or counter these alternatives?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
15	Alternatives	Question	Action Plan	14	If alternatives are unclear, whom will you ask — and what will you ask?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
16	Alternatives	Reminder		999			Identifying alternatives early prevents surprises, sharpens positioning, and strengthens your ability to win before the deal is at risk.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	141
124	Our Solution Ranking	Behavior		0		Understands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed.		t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
125	Our Solution Ranking	Question	Current Ranking	1	How do the Finalizer and key Decision Influencers rank our solution versus alternatives?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
126	Our Solution Ranking	Question	Current Ranking	2	What evidence confirms this?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
127	Our Solution Ranking	Question	Differentiated Value	3	Which differentiators are viewed as essential and unique?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
128	Our Solution Ranking	Question	Differentiated Value	4	What has the Finalizer said about our value — especially beyond price?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
129	Our Solution Ranking	Question	Competitive Preference	5	Who favors a competitor, and why?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
130	Our Solution Ranking	Question	Competitive Preference	6	What advantages do they see?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
131	Our Solution Ranking	Question	Objections & Repositioning	7	How do you respond to “so what?” challenges?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
132	Our Solution Ranking	Question	Objections & Repositioning	8	How are you reframing the conversation from price to outcomes?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
133	Our Solution Ranking	Question	Mentor Influence	9	How is your Mentor validating, reinforcing, or improving our ranking?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
134	Our Solution Ranking	Question	ROI & Success Measures	10	How will the customer define success or ROI?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
135	Our Solution Ranking	Question	ROI & Success Measures	11	What outcomes matter most?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
136	Our Solution Ranking	Question	Momentum & Next Actions	12	Is our ranking improving, stalled, or declining — and why?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
137	Our Solution Ranking	Question	Momentum & Next Actions	13	If unclear or weak, who will you ask next and what will you change?			t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
138	Our Solution Ranking	Reminder		999			Winning isn’t about being liked. It’s about being ranked #1 by the right Decision Influencers, for the right reasons, when it matters.	t	2025-12-16 19:46:44.519144	2025-12-16 19:46:44.519144	142
\.


--
-- Data for Name: checklist_item_notes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.checklist_item_notes (id, checklist_item_id, session_id, customer_name, opportunity_name, opportunity_key, note_text, decision_influencers, created_by_user_id, updated_by_user_id, is_active, version, previous_version_id, created_at, updated_at, structured_content) FROM stdin;
36	134	87	Acme Enterprise	Q4 Enterprise Deal	42919883366b878b6efb95d7e52e8cfb17d73fa24ded399bc1409bbfc1714fa4	Test 1	null	14	14	f	1	\N	2026-04-01 10:48:54.047848	2026-04-01 10:51:34.086919	null
37	134	87	Acme Enterprise	Q4 Enterprise Deal	42919883366b878b6efb95d7e52e8cfb17d73fa24ded399bc1409bbfc1714fa4	Test 2	null	14	14	f	2	36	2026-04-01 10:51:34.53203	2026-04-01 10:56:47.758639	null
39	134	87	Acme Enterprise	Q4 Enterprise Deal	42919883366b878b6efb95d7e52e8cfb17d73fa24ded399bc1409bbfc1714fa4	Test 4 - Update	null	14	14	f	4	\N	2026-04-01 10:59:04.907347	2026-04-01 11:19:25.951551	null
43	135	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	Notes for testing purpose	null	14	14	t	1	\N	2026-04-01 18:46:14.73114	2026-04-01 18:46:14.731144	null
44	136	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	\N	null	14	14	t	1	\N	2026-04-01 18:46:31.775713	2026-04-01 18:47:04.490043	{"date": "01-04-2026", "quantity": "150"}
45	137	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	Notes for testing purpose	null	14	14	t	1	\N	2026-04-01 18:47:34.919706	2026-04-01 18:47:34.919709	null
42	134	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	Notes for testing purpose ghq	null	14	14	t	1	\N	2026-04-01 18:45:40.747937	2026-04-06 10:02:42.50639	null
46	138	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	\N	null	14	14	t	1	\N	2026-04-01 18:48:12.78862	2026-04-17 18:07:59.909347	{"utilizer": {"names": ["ABC - TU"], "results": ["ABC - R2"]}, "finalizer": {"names": ["ABC - TF", "XYZ-TF"], "results": ["ABC - R1"]}, "specifiers": {"names": ["ABC - TS"], "results": ["ABC - R3"]}}
48	140	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	Test	null	14	14	t	1	\N	2026-04-29 07:05:55.654226	2026-04-29 07:05:55.65424	null
49	141	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	testing	null	14	14	t	1	\N	2026-04-29 07:06:17.417092	2026-04-29 07:06:17.417105	null
50	142	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	Testing	null	14	14	t	1	\N	2026-04-29 07:06:40.519855	2026-04-29 07:06:40.519867	null
51	143	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	\N	null	14	14	t	1	\N	2026-04-29 07:07:43.245588	2026-04-29 07:07:43.245601	{"utilizer": {"wiifm": ["Tester 1", "Tester 2"], "results": ["Tester 1", "Tester 2"]}, "finalizer": {"wiifm": ["Tester 1", "Tester 2"], "results": ["Tester 1", "Tester 2"]}, "specifiers": {"wiifm": ["Tester 1", "Tester 2"], "results": ["Tester 1", "Tester 2"]}}
47	139	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	\N	null	14	14	f	1	\N	2026-04-29 07:03:49.916699	2026-04-29 07:19:23.519381	{"mentors": [{"name": "ABC", "email": "test2@test.com", "phone": "+12867676767", "title": "test 2"}]}
52	139	95	Acme Corporation	Q2 Software Implementation	ffa630807c926f8e537c3e3647f0695a3c272d94f0efc6b72a19ae0530fe6d41	\N	null	14	14	t	2	47	2026-04-29 07:19:25.006693	2026-04-29 07:19:25.006703	{"mentors": [{"name": "XYZ", "email": "test1@test.com", "phone": "+12787787878", "title": "test1@test.com"}]}
63	134	99	Test	Test	18e47ca76de2e5e7407d2db7dccf5c557ef30955ea542f4bed70260fdffe4758	Customer fit notes test	null	14	14	t	1	\N	2026-05-07 18:42:13.837768	2026-05-07 18:42:13.837772	null
64	135	99	Test	Test	18e47ca76de2e5e7407d2db7dccf5c557ef30955ea542f4bed70260fdffe4758	Test notes	null	14	14	t	1	\N	2026-05-07 18:42:39.832046	2026-05-07 18:42:39.83205	null
65	136	99	Test	Test	18e47ca76de2e5e7407d2db7dccf5c557ef30955ea542f4bed70260fdffe4758	\N	null	14	14	t	1	\N	2026-05-07 18:42:58.875216	2026-05-07 18:42:58.875219	{"date": "07-05-2026", "quantity": "100"}
66	138	99	Test	Test	18e47ca76de2e5e7407d2db7dccf5c557ef30955ea542f4bed70260fdffe4758	\N	null	14	14	t	1	\N	2026-05-07 18:43:21.178974	2026-05-07 18:43:21.178979	{"utilizer": {"names": ["Tester"], "results": []}, "finalizer": {"names": ["Dave"], "results": []}, "specifiers": {"names": ["Test"], "results": []}}
53	134	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	Test	null	\N	\N	t	1	\N	2026-04-29 16:44:54.629095	2026-04-29 16:44:54.629107	null
54	135	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	Test	null	\N	\N	t	1	\N	2026-04-29 16:44:59.01726	2026-04-29 16:44:59.017272	null
55	136	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	\N	null	\N	\N	t	1	\N	2026-04-29 16:45:32.748021	2026-04-29 16:45:32.74803	{"date": "29-04-2026", "quantity": "1000"}
56	137	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	Test	null	\N	\N	t	1	\N	2026-04-29 16:45:49.509549	2026-04-29 16:45:49.509561	null
57	138	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	\N	null	\N	\N	t	1	\N	2026-04-29 16:46:18.694333	2026-04-29 16:46:18.694345	{"utilizer": {"names": ["Test name"], "results": ["Test result"]}, "finalizer": {"names": ["Test name"], "results": ["Test result"]}, "specifiers": {"names": ["Test name"], "results": ["Test result"]}}
58	139	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	\N	null	\N	\N	t	1	\N	2026-04-29 16:47:01.06067	2026-04-29 16:47:01.060683	{"mentors": [{"name": "Test name", "email": "testemail@test.com", "phone": "+9231340449788", "title": "Test title"}]}
59	140	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	Test	null	\N	\N	t	1	\N	2026-04-29 16:47:14.614271	2026-04-29 16:47:14.61429	null
60	141	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	Test	null	\N	\N	t	1	\N	2026-04-29 16:47:26.981995	2026-04-29 16:47:26.982008	null
61	142	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	Test	null	\N	\N	t	1	\N	2026-04-29 16:47:44.9165	2026-04-29 16:47:44.916515	null
62	143	\N	Test 29 April	Test 29 April	8be66af55fb5bc0b6c1b5d77f4bc191e7594e88aab0c9de6bfee0c9b14c24cf5	\N	null	\N	\N	t	1	\N	2026-04-29 16:48:07.857104	2026-04-29 16:48:07.857408	{"utilizer": {"wiifm": ["Test result"], "results": ["Test name"]}, "finalizer": {"wiifm": ["Test result"], "results": ["Test name"]}, "specifiers": {"wiifm": ["Test result"], "results": ["Test name"]}}
\.


--
-- Data for Name: checklist_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.checklist_items (id, category_id, title, definition, "order", is_active, created_at, updated_at) FROM stdin;
134	52	Customer Fit	A) Decision Influencers (DIs) are accessible.  B) DIs appreciate our brand and value.  C) Meets minimum size. D) DIs practice open and honest communication. E) And the opportunity is worth my time.	1	t	2025-12-03 15:18:41.579365	2025-12-03 15:18:41.579372
135	52	Trigger Event & Impact (Results)	A) I know what’s causing the DIs to want to make a buying decision. B) And the measurable results they are seeking.	2	t	2025-12-03 15:18:41.579375	2025-12-03 15:18:41.579377
136	52	Sales Target	A) I know what they are planning on buying, how much and when.	3	t	2025-12-03 15:18:41.579379	2025-12-03 15:18:41.579381
138	52	Decision Influencers (DI)	A) I have identified AND engaged the key Specifiers, Utilizers and the Finalizer.	5	t	2025-12-03 15:18:41.579388	2025-12-03 15:18:41.57939
139	52	Mentor	A) I have developed someone who wants me to be successful. B) And is able to make things happen with the other Decision Influencers.	6	t	2025-12-03 15:18:41.579392	2025-12-03 15:18:41.579394
140	52	Trigger Priority	A) I have validated that all the key Decision Influencers believe this project is a priority.	7	t	2025-12-03 15:18:41.579396	2025-12-03 15:18:41.579398
141	52	Alternatives	A) I have identified all of the key DIs Alternatives for the investment (including the Finalizer). B) And developed appropriate strategies.	8	t	2025-12-03 15:18:41.5794	2025-12-03 15:18:41.579402
142	52	Our Solution Ranking	A) Our Solution uniquely solves the Trigger Event.	9	t	2025-12-03 15:18:41.579405	2025-12-03 15:18:41.579407
143	52	Individual Impact	A) I have identified how all the key DIs will be personally impacted when we Solve the Trigger Event with our Solution.	10	t	2025-12-03 15:18:41.579409	2025-12-03 15:18:41.579411
137	52	Decision Making Process	A) I have identified the steps in the DMP. B) The criteria they are going to use to evaluate solutions. C) Who is impacting the decision. D) When they are making the decision. E) And verified the project has or can get funding.	4	t	2025-12-03 15:18:41.579384	2025-12-03 15:18:41.579386
\.


--
-- Data for Name: coaching_feedback; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coaching_feedback (id, session_id, feedback_text, strengths, improvement_areas, action_items, generated_at, openai_request_id, created_at, updated_at) FROM stdin;
40	87	Excellent work! You achieved a perfect score of 100/100 on this call. All checklist items were successfully completed. Keep up the great work and continue applying these best practices in your future calls.	[]	[]	["Continue applying these successful techniques in future calls"]	2026-03-31 15:36:43.404387	\N	2026-03-31 15:36:43.409573	2026-03-31 15:36:43.409581
41	89	Excellent work! You achieved a perfect score of 100/100 on this call. All checklist items were successfully completed. Keep up the great work and continue applying these best practices in your future calls.	[]	[]	["Continue applying these successful techniques in future calls"]	2026-04-01 15:33:11.556086	\N	2026-04-01 15:33:11.560877	2026-04-01 15:33:11.560885
49	100	Coaching Feedback for Test 2 - Test 2\nScore: 30/100 | Risk Band: RED\n\n**Trigger Event & Impact (Results):**\nClearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured.\n\n**Decision Making Process:**\nUnderstands — from the customer's perspective — what they are buying, how much, why, when, and how the decision will be made. Verified through evidence, not assumption.\n\n**Mentor:**\nDevelops true Mentors, validates their commitment through actions, and leverages them strategically throughout the pursuit.\n\n**Trigger Priority:**\nRecognizes that even when a company is buying (RFQ/RFP), urgency varies by Decision Influencer — and validates priority individually, not collectively.\n\n**Alternatives:**\nSystematically identifies all alternatives — competitors, internal options, and "do nothing" — understands who supports each and uses that insight to differentiate and reduce risk.\n\n**Our Solution Ranking:**\nUnderstands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed.\n\n**Individual Impact:**\nUnderstands that people buy, companies do not and seeks to link their product or service to what is important to each individual key Decision Influencer in a manner that the competition cannot.	[]	[{"point": "Trigger Event & Impact (Results)", "explanation": "Clearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured."}, {"point": "Decision Making Process", "explanation": "Understands \\u2014 from the customer's perspective \\u2014 what they are buying, how much, why, when, and how the decision will be made. Verified through evidence, not assumption."}, {"point": "Mentor", "explanation": "Develops true Mentors, validates their commitment through actions, and leverages them strategically throughout the pursuit."}, {"point": "Trigger Priority", "explanation": "Recognizes that even when a company is buying (RFQ/RFP), urgency varies by Decision Influencer \\u2014 and validates priority individually, not collectively."}, {"point": "Alternatives", "explanation": "Systematically identifies all alternatives \\u2014 competitors, internal options, and \\"do nothing\\" \\u2014 understands who supports each and uses that insight to differentiate and reduce risk."}, {"point": "Our Solution Ranking", "explanation": "Understands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed."}, {"point": "Individual Impact", "explanation": "Understands that people buy, companies do not and seeks to link their product or service to what is important to each individual key Decision Influencer in a manner that the competition cannot."}]	["Review the gaps above and prepare specific questions for your next call"]	2026-05-26 15:53:50.206972	\N	2026-05-26 15:53:50.207479	2026-05-26 15:53:50.207481
42	90	Coaching Feedback for Test 2 - Test 2\nScore: 60/100 | Risk Band: YELLOW\n\n**Trigger Event & Impact (Results):**\nClearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured.\n\n**Decision Influencers (DI):**\nSpecifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought.\n\n**Trigger Priority:**\nRecognizes that even when a company is buying (RFQ/RFP), urgency varies by Decision Influencer — and validates priority individually, not collectively.\n\n**Individual Impact:**\nUnderstands that people buy, companies do not and seeks to link their product or service to what is important to each individual key Decision Influencer in a manner that the competition cannot.	[]	[{"point": "Trigger Event & Impact (Results)", "explanation": "Clearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured."}, {"point": "Decision Influencers (DI)", "explanation": "Specifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought."}, {"point": "Trigger Priority", "explanation": "Recognizes that even when a company is buying (RFQ/RFP), urgency varies by Decision Influencer \\u2014 and validates priority individually, not collectively."}, {"point": "Individual Impact", "explanation": "Understands that people buy, companies do not and seeks to link their product or service to what is important to each individual key Decision Influencer in a manner that the competition cannot."}]	["Review the gaps above and prepare specific questions for your next call"]	2026-04-01 15:44:58.927475	\N	2026-04-01 15:44:58.92921	2026-04-01 15:44:58.929216
43	93	Coaching Feedback for Farooq Testing - Test\nScore: 70/100 | Risk Band: GREEN\n\n**Decision Influencers (DI):**\nSpecifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought.\n\n**Mentor:**\nDevelops true Mentors, validates their commitment through actions, and leverages them strategically throughout the pursuit.\n\n**Our Solution Ranking:**\nUnderstands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed.	[]	[{"point": "Decision Influencers (DI)", "explanation": "Specifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought."}, {"point": "Mentor", "explanation": "Develops true Mentors, validates their commitment through actions, and leverages them strategically throughout the pursuit."}, {"point": "Our Solution Ranking", "explanation": "Understands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed."}]	["Review the gaps above and prepare specific questions for your next call"]	2026-04-01 16:13:42.478269	\N	2026-04-01 16:13:42.484927	2026-04-01 16:13:42.484943
44	94	Coaching Feedback for Test 3 - Testing 3\nScore: 80/100 | Risk Band: GREEN\n\n**Trigger Event & Impact (Results):**\nClearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured.\n\n**Decision Influencers (DI):**\nSpecifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought.	[]	[{"point": "Trigger Event & Impact (Results)", "explanation": "Clearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured."}, {"point": "Decision Influencers (DI)", "explanation": "Specifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought."}]	["Review the gaps above and prepare specific questions for your next call"]	2026-04-01 16:31:58.324837	\N	2026-04-01 16:31:58.326584	2026-04-01 16:31:58.326591
45	95	Coaching Feedback for Acme Corporation - Q2 Software Implementation\nScore: 90/100 | Risk Band: GREEN\n\n**Trigger Event & Impact (Results):**\nClearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured.	[]	[{"point": "Trigger Event & Impact (Results)", "explanation": "Clearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured."}]	["Review the gaps above and prepare specific questions for your next call"]	2026-04-01 18:44:49.254055	\N	2026-04-01 18:44:49.255481	2026-04-01 18:44:49.255482
46	96	Coaching Feedback for Acme Corporation - Q2 Software Implementation\nScore: 70/100 | Risk Band: GREEN\n\n**Sales Target:**\nUnderstands — from the customer's perspective — what they are planning to buy, how much, why, when, and how the decision will be made.\n\n**Alternatives:**\nSystematically identifies all alternatives — competitors, internal options, and "do nothing" — understands who supports each and uses that insight to differentiate and reduce risk.\n\n**Decision Making Process:**\nUnderstands — from the customer's perspective — what they are buying, how much, why, when, and how the decision will be made. Verified through evidence, not assumption.	[]	[{"point": "Sales Target", "explanation": "Understands \\u2014 from the customer's perspective \\u2014 what they are planning to buy, how much, why, when, and how the decision will be made."}, {"point": "Alternatives", "explanation": "Systematically identifies all alternatives \\u2014 competitors, internal options, and \\"do nothing\\" \\u2014 understands who supports each and uses that insight to differentiate and reduce risk."}, {"point": "Decision Making Process", "explanation": "Understands \\u2014 from the customer's perspective \\u2014 what they are buying, how much, why, when, and how the decision will be made. Verified through evidence, not assumption."}]	["Review the gaps above and prepare specific questions for your next call"]	2026-04-06 10:03:16.4031	\N	2026-04-06 10:03:16.404616	2026-04-06 10:03:16.404618
48	99	Excellent work! You achieved a perfect score of 60/100 on this call. All checklist items were successfully completed. Keep up the great work and continue applying these best practices in your future calls.	[]	[]	["Continue applying these successful techniques in future calls"]	2026-05-07 18:48:57.371356	\N	2026-05-07 18:48:57.372642	2026-05-07 18:48:57.372644
50	101	Coaching Feedback for Farooq Testing - Q2 Software Implementation\nScore: 70/100 | Risk Band: GREEN\n\n**Trigger Event & Impact (Results):**\nClearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured.\n\n**Decision Influencers (DI):**\nSpecifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought.\n\n**Our Solution Ranking:**\nUnderstands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed.	[]	[{"point": "Trigger Event & Impact (Results)", "explanation": "Clearly identifies why Decision Influencers want to change now, the event or condition driving urgency, and how success will be measured."}, {"point": "Decision Influencers (DI)", "explanation": "Specifiers define what gets bought. Utilizers decide if it will work. Finalizers decide whether it gets bought."}, {"point": "Our Solution Ranking", "explanation": "Understands how Decision Influencers rank the solution itself, confirms whether differentiators are essential and unique, and actively shifts negative perceptions when needed."}]	["Review the gaps above and prepare specific questions for your next call"]	2026-06-09 12:44:59.296014	\N	2026-06-09 12:44:59.299909	2026-06-09 12:44:59.299921
\.


--
-- Data for Name: coaching_questions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coaching_questions (id, item_id, section, question, "order", is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: invitations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.invitations (id, email, organization_id, team_id, role, token, invited_by, expires_at, accepted_at, created_at, updated_at) FROM stdin;
15	hafizfarooq78692@gmail.com	5	6	rep	nJIoZLMMZelmUtl7IqSh58HY3qf-0jmsyCwizLcTgY0	11	2026-05-06 15:22:23.478292	2026-04-29 15:23:49.523236	2026-04-29 15:22:24.496738	2026-04-29 15:23:49.525868
16	dave@millaugroupglobal.com	5	4	manager	wLSm4Lh1JOe7FnTjucoYfprhD9NQFWWfR9hfi4K3pvQ	11	2026-05-15 18:04:19.278741	\N	2026-05-08 18:04:20.14205	2026-05-08 18:04:20.142054
17	fahadmuhammad661@gmail.com	5	6	rep	V_LQR8AHmNVlw7kn6iWeXdybvQ93S2Ao7vEaPTukNfM	11	2026-05-15 18:05:39.476815	\N	2026-05-08 18:05:40.292122	2026-05-08 18:05:40.292125
18	davevarner@mac.com	7	\N	admin	dsqtQfZcxOVAYvaUWEwNRpexkFKqZsfy_2DyAZhpmPg	15	2026-06-20 17:49:21.835214	\N	2026-06-13 17:49:22.855515	2026-06-13 17:49:22.855528
19	hafizfarooq78692@gmail.com	5	4	manager	nDANx3kwdeIEOZUIJ2ZIOYnDq7A5mPrvknlWJU6ee0o	11	2026-06-21 16:00:46.746901	2026-06-14 16:02:27.041381	2026-06-14 15:25:58.900007	2026-06-14 16:02:27.043326
\.


--
-- Data for Name: manager_notes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.manager_notes (id, session_id, manager_id, note_text, is_edited, created_at, updated_at, note_type, audio_s3_bucket, audio_s3_key, audio_duration, audio_file_size) FROM stdin;
19	96	11	Test	f	2026-04-17 20:11:22.180382	2026-04-17 20:11:22.180386	TEXT	\N	\N	\N	\N
\.


--
-- Data for Name: organization_registration_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.organization_registration_requests (id, status, company_name, industry, logo_url, admin_first_name, admin_last_name, admin_email, admin_direct_dial, admin_cell_phone, additional_users, organization_id, reviewed_by, reviewed_at, rejection_reason, created_at, updated_at) FROM stdin;
1	approved	The Sales Checklist	Professional Services	pending-registrations/1/logo-1dec4e1d78b842629589277e4f26d6f2.png	David	Varner	davevarner@mac.com	(212) 456-7890	\N	[]	7	15	2026-06-13 17:49:31.165872	\N	2026-06-13 16:52:59.753254	2026-06-13 17:49:31.168186
\.


--
-- Data for Name: organization_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.organization_settings (id, organization_id, allow_self_registration, default_role, logo_url, primary_color, settings, created_at, updated_at, executive_sponsor_name, executive_sponsor_email, executive_sponsor_direct_dial, executive_sponsor_cell_phone) FROM stdin;
1	5	f	rep	branding/5/logo-2417f2f3c0d340b397573c960052d33b.png	#484d60	{}	2025-12-30 09:33:31.84714	2026-06-13 15:02:16.295878	\N	\N	\N	\N
3	7	f	rep	branding/7/logo-34cc48e185a047b483d810afcebe9d08.png	\N	{}	2026-06-13 17:49:19.539363	2026-06-13 17:49:19.539372	\N	\N	\N	\N
\.


--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.organizations (id, name, is_active, created_at, updated_at, industry) FROM stdin;
5	The Millau Group Global	t	2025-12-05 15:12:43.17364	2026-06-13 14:48:42.030239	Retail
7	The Sales Checklist	t	2026-06-13 17:48:31.522661	2026-06-13 17:48:31.522672	Professional Services
\.


--
-- Data for Name: reports; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reports (id, session_id, pdf_s3_bucket, pdf_s3_key, pdf_file_size, generated_at, is_generated, emailed_at, emailed_to, created_at, updated_at) FROM stdin;
35	95	sales-checklist-reports	reports/13/95/Acme_Corporation_20260508_175844.pdf	449128	2026-05-08 17:58:46.552432	t	\N	\N	2026-04-17 17:11:41.314025	2026-05-08 17:58:46.55296
38	99	sales-checklist-reports	reports/13/99/Test_20260512_232632.pdf	447719	2026-05-12 23:26:35.249869	t	\N	\N	2026-05-07 18:49:05.964916	2026-05-12 23:26:35.250391
37	94	sales-checklist-reports	reports/13/94/Test_3_20260512_233010.pdf	448192	2026-05-12 23:30:13.414132	t	\N	\N	2026-05-07 18:25:01.975555	2026-05-12 23:30:13.414608
39	100	sales-checklist-reports	reports/14/100/Test_2_20260526_155453.pdf	448185	2026-05-26 15:54:56.638124	t	\N	\N	2026-05-26 15:53:56.365215	2026-05-26 15:54:56.638659
41	87	sales-checklist-reports	reports/11/87/Acme_Enterprise_20260609_170453.pdf	129039	2026-06-09 17:04:54.614377	t	\N	\N	2026-06-09 17:04:54.616479	2026-06-09 17:04:54.616481
40	101	sales-checklist-reports	reports/11/101/Farooq_Testing_20260613_153550.pdf	63417	2026-06-13 15:35:52.369436	t	\N	\N	2026-06-09 12:45:10.693987	2026-06-13 15:35:52.373553
34	96	sales-checklist-reports	reports/11/96/Acme_Corporation_20260417_201011.pdf	3439	2026-04-17 20:10:12.766913	t	\N	\N	2026-04-06 10:05:18.807563	2026-04-17 20:10:12.767844
\.


--
-- Data for Name: score_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.score_history (id, session_id, scoring_result_id, total_score, risk_band, items_validated, items_total, calculated_at, score_change, trigger_event, created_by_user_id, created_at, updated_at, version_number, changes_count, responses_snapshot) FROM stdin;
14	87	\N	100	GREEN	10	10	2026-03-31 15:36:36.623306	\N	initial_submission	14	2026-03-31 15:36:37.104168	2026-03-31 15:36:37.104175	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": true, "score": 10}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 137, "answer": true, "score": 10}, {"item_id": 138, "answer": true, "score": 10}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}]
15	87	49	100	GREEN	10	10	2026-03-31 16:41:27.853295	0	resubmission	13	2026-03-31 16:41:27.854975	2026-03-31 16:41:27.854977	2	0	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": true, "score": 10}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 137, "answer": true, "score": 10}, {"item_id": 138, "answer": true, "score": 10}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}]
16	89	50	100	GREEN	10	10	2026-04-01 15:33:08.342492	\N	initial_submission	14	2026-04-01 15:33:08.832517	2026-04-01 15:33:08.832527	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": true, "score": 10}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 138, "answer": true, "score": 10}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}, {"item_id": 137, "answer": true, "score": 10}]
17	90	51	60	YELLOW	6	10	2026-04-01 15:44:52.83519	\N	initial_submission	14	2026-04-01 15:44:53.305409	2026-04-01 15:44:53.305416	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": false, "score": 0}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 138, "answer": false, "score": 0}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": false, "score": 0}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": false, "score": 0}, {"item_id": 137, "answer": true, "score": 10}]
18	93	52	70	GREEN	7	10	2026-04-01 16:13:36.40654	\N	initial_submission	14	2026-04-01 16:13:36.939691	2026-04-01 16:13:36.939698	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": true, "score": 10}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 138, "answer": false, "score": 0}, {"item_id": 139, "answer": false, "score": 0}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": false, "score": 0}, {"item_id": 143, "answer": true, "score": 10}, {"item_id": 137, "answer": true, "score": 10}]
25	99	59	60	YELLOW	6	6	2026-05-07 18:48:47.692277	\N	initial_submission	14	2026-05-07 18:48:49.625623	2026-05-07 18:48:49.625627	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": true, "score": 10}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}]
19	94	53	80	GREEN	8	10	2026-04-01 16:31:50.65504	\N	initial_submission	14	2026-04-01 16:31:51.172699	2026-04-01 16:31:51.17271	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": false, "score": 0}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 138, "answer": false, "score": 0}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}, {"item_id": 137, "answer": true, "score": 10}]
20	95	54	90	GREEN	9	10	2026-04-01 18:44:45.113661	\N	initial_submission	14	2026-04-01 18:44:45.56321	2026-04-01 18:44:45.563213	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": false, "score": 0}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 138, "answer": true, "score": 10}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}, {"item_id": 137, "answer": true, "score": 10}]
21	96	\N	70	GREEN	7	10	2026-04-06 10:03:11.98175	\N	initial_submission	14	2026-04-06 10:03:12.408039	2026-04-06 10:03:12.408042	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": true, "score": 10}, {"item_id": 136, "answer": false, "score": 0}, {"item_id": 138, "answer": true, "score": 10}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": false, "score": 0}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}, {"item_id": 137, "answer": false, "score": 0}]
22	96	\N	80	GREEN	8	10	2026-04-06 10:03:55.087042	10	resubmission	14	2026-04-06 10:03:55.087668	2026-04-06 10:03:55.08767	2	1	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": true, "score": 10}, {"item_id": 138, "answer": true, "score": 10}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": false, "score": 0}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}, {"item_id": 137, "answer": false, "score": 0}, {"item_id": 136, "answer": true, "score": 10}]
23	96	57	50	YELLOW	5	10	2026-04-17 20:09:45.39406	-30	resubmission	11	2026-04-17 20:09:45.395968	2026-04-17 20:09:45.39597	3	3	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": false, "score": 0}, {"item_id": 142, "answer": true, "score": 10}, {"item_id": 143, "answer": true, "score": 10}, {"item_id": 137, "answer": false, "score": 0}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 135, "answer": false, "score": 0}, {"item_id": 138, "answer": false, "score": 0}, {"item_id": 139, "answer": false, "score": 0}]
26	100	60	30	RED	3	10	2026-05-26 15:53:41.888739	\N	initial_submission	14	2026-05-26 15:53:42.345512	2026-05-26 15:53:42.345516	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": false, "score": 0}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 137, "answer": false, "score": 0}, {"item_id": 138, "answer": true, "score": 10}, {"item_id": 139, "answer": false, "score": 0}, {"item_id": 140, "answer": false, "score": 0}, {"item_id": 141, "answer": false, "score": 0}, {"item_id": 142, "answer": false, "score": 0}, {"item_id": 143, "answer": false, "score": 0}]
27	101	61	70	GREEN	7	10	2026-06-09 12:44:48.429791	\N	initial_submission	14	2026-06-09 12:44:49.045469	2026-06-09 12:44:49.045478	1	\N	[{"item_id": 134, "answer": true, "score": 10}, {"item_id": 135, "answer": false, "score": 0}, {"item_id": 136, "answer": true, "score": 10}, {"item_id": 137, "answer": true, "score": 10}, {"item_id": 138, "answer": false, "score": 0}, {"item_id": 139, "answer": true, "score": 10}, {"item_id": 140, "answer": true, "score": 10}, {"item_id": 141, "answer": true, "score": 10}, {"item_id": 142, "answer": false, "score": 0}, {"item_id": 143, "answer": true, "score": 10}]
\.


--
-- Data for Name: scoring_results; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scoring_results (id, session_id, total_score, risk_band, category_scores, top_strengths, top_gaps, items_validated, items_total, created_at, updated_at) FROM stdin;
54	95	90	GREEN	{"52": {"name": "Sales Checklist", "score": 90, "max_score": 100}}	[]	[]	9	10	2026-04-01 18:44:43.752975	2026-05-08 17:58:40.961504
59	99	100	GREEN	{"52": {"name": "Sales Checklist", "score": 60, "max_score": 60}}	[]	[]	6	6	2026-05-07 18:48:44.681966	2026-05-12 23:26:23.750023
53	94	80	GREEN	{"52": {"name": "Sales Checklist", "score": 80, "max_score": 100}}	[]	[]	8	10	2026-04-01 16:31:48.424436	2026-05-12 23:30:06.509726
60	100	30	RED	{"52": {"name": "Sales Checklist", "score": 30, "max_score": 100}}	[]	[]	3	10	2026-05-26 15:53:38.911179	2026-05-26 15:54:48.249188
49	87	100	GREEN	{"52": {"name": "Sales Checklist", "score": 100, "max_score": 100}}	[]	[]	10	10	2026-03-31 16:41:26.992462	2026-06-09 17:04:48.889192
50	89	100	GREEN	{}	[]	[]	10	10	2026-04-01 15:33:06.766394	2026-04-01 15:33:06.766403
51	90	60	YELLOW	{}	[]	[]	6	10	2026-04-01 15:44:50.897141	2026-04-01 15:44:50.897161
52	93	70	GREEN	{}	[]	[]	7	10	2026-04-01 16:13:32.647119	2026-04-01 16:13:32.647127
57	96	50	YELLOW	{"52": {"name": "Sales Checklist", "score": 50, "max_score": 100}}	[]	[]	5	10	2026-04-17 20:09:44.499891	2026-04-17 20:10:09.636364
61	101	70	GREEN	{"52": {"name": "Sales Checklist", "score": 70, "max_score": 100}}	[]	[]	7	10	2026-06-09 12:44:44.651834	2026-06-13 15:35:43.465891
\.


--
-- Data for Name: session_response_analysis; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.session_response_analysis (id, session_response_id, behaviour_id, evidence_found, evidence_text, ai_reasoning, confidence_score, created_at) FROM stdin;
1808	857	85	t	We have met with multiple decision influencers.	Senior leadership is accessible and engaged.	\N	2026-04-01 15:32:20.785573
1809	857	86	t	They appreciate the brand Deck Pro Prestige.	They understand and value our differentiation.	\N	2026-04-01 15:32:20.785573
1810	857	87	t	They appreciate the brand and the value.	Evidence of real value alignment.	\N	2026-04-01 15:32:20.785573
1811	857	88	t	Influencers from the key decision influencers...show interest.	Decision Influencers appreciate our brand.	\N	2026-04-01 15:32:20.785573
1812	857	89	f	\N	No signs of commoditization were discussed.	\N	2026-04-01 15:32:20.785573
1813	857	90	t	Open and honest communication with us.	Demonstrated openness and honesty.	\N	2026-04-01 15:32:20.785573
1814	857	91	t	Opportunity is worth my time.	Fit criteria are validated.	\N	2026-04-01 15:32:20.785573
1815	857	92	t	We have met with multiple decision influencers.	Conversations confirm Fit.	\N	2026-04-01 15:32:20.785573
1816	857	93	t	Annual potential of almost $1 million.	Estimated size of the opportunity is known.	\N	2026-04-01 15:32:20.785573
1817	857	94	t	Opportunity is worth my time.	Fit assessment shapes next steps.	\N	2026-04-01 15:32:20.785573
1818	857	95	f	\N	Not discussed.	\N	2026-04-01 15:32:20.785573
1819	857	96	f	\N	Not discussed.	\N	2026-04-01 15:32:20.785573
1820	857	97	f	\N	Not discussed.	\N	2026-04-01 15:32:20.785573
1821	857	98	f	\N	Not discussed.	\N	2026-04-01 15:32:20.785573
1822	858	114	t	They are tired of a product in the marketplace.	Driving factor and outcomes are identified.	\N	2026-04-01 15:32:20.785573
1823	858	115	t	They don't like creating a lot of demand and losing it.	Real Trigger Event is addressed.	\N	2026-04-01 15:32:20.785573
1824	858	116	t	Vendor community sets up additional dealerships.	Incident creating urgency is identified.	\N	2026-04-01 15:32:20.785573
1825	858	117	f	\N	Success measurement not explicitly discussed.	\N	2026-04-01 15:32:20.785573
1826	858	118	f	\N	Confirmation of Trigger Event not discussed.	\N	2026-04-01 15:32:20.785573
1827	858	119	f	\N	Not discussed.	\N	2026-04-01 15:32:20.785573
1828	858	120	f	\N	No deeper issues uncovered.	\N	2026-04-01 15:32:20.785573
1829	858	121	f	\N	Not discussed.	\N	2026-04-01 15:32:20.785573
1830	858	122	f	\N	Not discussed.	\N	2026-04-01 15:32:20.785573
1831	859	73	t	Met with multiple decision influencers.	Engaged with decision makers.	\N	2026-04-01 15:32:20.785573
1832	859	74	t	We recognized that six months ago.	Engagement plan is in place.	\N	2026-04-01 15:32:20.785573
1833	859	75	t	Initially they will buy a full truckload.	Purchase quantity and timing are known.	\N	2026-04-01 15:32:20.785573
1834	859	76	t	If there's any decisions to be made, it's now.	Timing urgency is understood.	\N	2026-04-01 15:32:20.785573
1835	859	77	t	We do understand the sales target.	Solution matches intended purchase.	\N	2026-04-01 15:32:20.785573
1836	859	78	f	\N	Evaluation criteria not discussed.	\N	2026-04-01 15:32:20.785573
1837	859	79	t	Plenty of funding and good standing credit.	Funding is confirmed.	\N	2026-04-01 15:32:20.785573
1838	859	80	f	\N	Internal risks not discussed.	\N	2026-04-01 15:32:20.785573
1839	859	81	f	\N	Add-on opportunities not discussed.	\N	2026-04-01 15:32:20.785573
1840	859	82	f	\N	Unknowns not discussed.	\N	2026-04-01 15:32:20.785573
1841	860	31	t	Met with all decision influencers.	Specifiers identified.	\N	2026-04-01 15:32:20.785573
1842	860	32	f	\N	Verification of roles not discussed.	\N	2026-04-01 15:32:20.785573
1843	860	33	f	\N	External consultants not mentioned.	\N	2026-04-01 15:32:20.785573
1844	860	34	f	\N	Specifications not discussed.	\N	2026-04-01 15:32:20.785573
1845	860	35	f	\N	Evaluation criteria not discussed.	\N	2026-04-01 15:32:20.785573
1846	860	36	t	Met with contractors.	Utilizers identified.	\N	2026-04-01 15:32:20.785573
1847	860	37	f	\N	Confirmation of roles not discussed.	\N	2026-04-01 15:32:20.785573
1848	860	38	f	\N	Utilizers' priorities not discussed.	\N	2026-04-01 15:32:20.785573
1849	860	39	f	\N	Impact on Utilizers not discussed.	\N	2026-04-01 15:32:20.785573
1850	860	40	t	Final decision influencer, which was his dad.	Finalizer identified.	\N	2026-04-01 15:32:20.785573
1851	860	41	t	Jordan set up meetings with each key decision influencer.	Engagement plan exists.	\N	2026-04-01 15:32:20.785573
1852	860	42	f	\N	Next steps after approval not discussed.	\N	2026-04-01 15:32:20.785573
1853	860	43	f	\N	Finalizer's values not discussed.	\N	2026-04-01 15:32:20.785573
1854	860	44	f	\N	Confirmation of timing not discussed.	\N	2026-04-01 15:32:20.785573
1855	860	45	f	\N	Influence on Finalizer not discussed.	\N	2026-04-01 15:32:20.785573
1856	860	46	f	\N	Unclear aspects not discussed.	\N	2026-04-01 15:32:20.785573
1857	861	140	t	We do have a mentor.	Mentor exists, indicating deal viability.	\N	2026-04-01 15:32:20.785573
1858	861	141	t	His name is Jordan.	Mentor identified with vested interest.	\N	2026-04-01 15:32:20.785573
1859	861	142	f	\N	Others' belief not discussed.	\N	2026-04-01 15:32:20.785573
1860	861	143	t	Jordan appreciates that.	Strong candidate identified.	\N	2026-04-01 15:32:20.785573
1861	861	144	f	\N	Replacement not discussed.	\N	2026-04-01 15:32:20.785573
1862	861	145	f	\N	Hesitant candidates not discussed.	\N	2026-04-01 15:32:20.785573
1863	861	146	t	Jordan appreciates that.	Mentor's commitment is evident.	\N	2026-04-01 15:32:20.785573
1864	861	147	f	\N	Exclusivity test not discussed.	\N	2026-04-01 15:32:20.785573
1865	861	148	t	Jordan set up meetings.	Mentor's actions advance position.	\N	2026-04-01 15:32:20.785573
1866	861	149	t	Jordan set up meetings.	Mentor influences other DIs.	\N	2026-04-01 15:32:20.785573
1867	861	150	f	\N	Strategic shifts not discussed.	\N	2026-04-01 15:32:20.785573
1868	861	151	f	\N	Non-public information not discussed.	\N	2026-04-01 15:32:20.785573
1869	861	152	f	\N	Competition's mentor not discussed.	\N	2026-04-01 15:32:20.785573
1870	861	153	f	\N	Secondary Mentor not discussed.	\N	2026-04-01 15:32:20.785573
1871	861	154	f	\N	Next steps to confirm Mentor not discussed.	\N	2026-04-01 15:32:20.785573
1872	861	155	f	\N	Explicit mentoring request not discussed.	\N	2026-04-01 15:32:20.785573
1873	861	156	f	\N	Risks not discussed.	\N	2026-04-01 15:32:20.785573
1874	861	157	f	\N	Project ranking not discussed.	\N	2026-04-01 15:32:20.785573
1875	861	158	f	\N	Biggest threat not discussed.	\N	2026-04-01 15:32:20.785573
1876	861	159	f	\N	Winners and losers not discussed.	\N	2026-04-01 15:32:20.785573
1877	861	160	f	\N	Alternatives not discussed.	\N	2026-04-01 15:32:20.785573
1878	861	161	f	\N	Mentor's additional support not discussed.	\N	2026-04-01 15:32:20.785573
1879	861	162	f	\N	Internal coaching not discussed.	\N	2026-04-01 15:32:20.785573
1880	862	18	t	Alignment in all priorities.	High priority confirmed for key DIs.	\N	2026-04-01 15:32:20.785573
1881	862	19	f	\N	No dissenting influencers discussed.	\N	2026-04-01 15:32:20.785573
1882	862	20	f	\N	Reasons for lower priority not discussed.	\N	2026-04-01 15:32:20.785573
1883	862	21	t	Priority not only at the final decision making level.	Priority confirmed for Finalizer.	\N	2026-04-01 15:32:20.785573
1884	862	22	t	Alignment in all priorities.	Proof of priority alignment.	\N	2026-04-01 15:32:20.785573
1885	862	23	f	\N	Other initiatives not discussed.	\N	2026-04-01 15:32:20.785573
1886	862	24	f	\N	Increasing urgency not discussed.	\N	2026-04-01 15:32:20.785573
1887	862	25	t	Jordan appreciates that.	Mentor validated priority levels.	\N	2026-04-01 15:32:20.785573
1888	862	26	f	\N	Insights on urgency not discussed.	\N	2026-04-01 15:32:20.785573
1889	862	27	f	\N	Unclear priority not discussed.	\N	2026-04-01 15:32:20.785573
1890	862	28	f	\N	Questions to uncover urgency not discussed.	\N	2026-04-01 15:32:20.785573
1891	863	2	t	Do nothing, keep the same product.	Alternatives identified.	\N	2026-04-01 15:32:20.785573
1892	863	3	t	They're not evaluating another product.	Customer's perception of alternatives known.	\N	2026-04-01 15:32:20.785573
1893	863	4	t	Do nothing is a viable option.	Cost of inaction identified.	\N	2026-04-01 15:32:20.785573
1894	863	5	f	\N	Support for alternatives not discussed.	\N	2026-04-01 15:32:20.785573
1895	863	6	f	\N	Reasons for advocating alternatives not discussed.	\N	2026-04-01 15:32:20.785573
1896	863	7	f	\N	Internal options not discussed.	\N	2026-04-01 15:32:20.785573
1897	863	8	f	\N	Politics and resources not discussed.	\N	2026-04-01 15:32:20.785573
1898	863	9	t	Westbury and Fortress Railing.	Competitors identified.	\N	2026-04-01 15:32:20.785573
1899	863	10	f	\N	Competitors' strengths and weaknesses not discussed.	\N	2026-04-01 15:32:20.785573
1900	863	11	f	\N	Our strengths and gaps not discussed.	\N	2026-04-01 15:32:20.785573
1901	863	12	f	\N	Differentiation strategy not discussed.	\N	2026-04-01 15:32:20.785573
1902	863	13	f	\N	Proof points not discussed.	\N	2026-04-01 15:32:20.785573
1903	863	14	f	\N	Mentor's role in alternatives not discussed.	\N	2026-04-01 15:32:20.785573
1904	863	15	f	\N	Unclear alternatives not discussed.	\N	2026-04-01 15:32:20.785573
1905	864	125	t	Our solution ranks right up there.	Solution ranking is high.	\N	2026-04-01 15:32:20.785573
1906	864	126	f	\N	Evidence of ranking not discussed.	\N	2026-04-01 15:32:20.785573
1907	864	127	f	\N	Differentiators not discussed.	\N	2026-04-01 15:32:20.785573
1908	864	128	f	\N	Finalizer's view on value not discussed.	\N	2026-04-01 15:32:20.785573
1909	864	129	f	\N	Competitor preference not discussed.	\N	2026-04-01 15:32:20.785573
1910	864	130	f	\N	Advantages of competitors not discussed.	\N	2026-04-01 15:32:20.785573
1911	864	131	f	\N	Response to challenges not discussed.	\N	2026-04-01 15:32:20.785573
1912	864	132	f	\N	Reframing conversation not discussed.	\N	2026-04-01 15:32:20.785573
1913	864	133	f	\N	Mentor's role in ranking not discussed.	\N	2026-04-01 15:32:20.785573
1914	864	134	f	\N	Success definition not discussed.	\N	2026-04-01 15:32:20.785573
1915	864	135	f	\N	Outcomes not discussed.	\N	2026-04-01 15:32:20.785573
1916	864	136	f	\N	Ranking changes not discussed.	\N	2026-04-01 15:32:20.785573
1917	864	137	f	\N	Unclear ranking not discussed.	\N	2026-04-01 15:32:20.785573
1918	865	101	t	We did get to learn that one of the biggest benefits...	Personal impact identified.	\N	2026-04-01 15:32:20.785573
1919	865	102	f	\N	Understanding of impact not discussed.	\N	2026-04-01 15:32:20.785573
1920	865	103	f	\N	Connection clarity not discussed.	\N	2026-04-01 15:32:20.785573
1921	865	104	f	\N	Competition's impact not discussed.	\N	2026-04-01 15:32:20.785573
1922	865	105	t	Providing some exclusivity.	Unique WIIFM identified.	\N	2026-04-01 15:32:20.785573
1923	865	106	f	\N	Positive impacts not discussed.	\N	2026-04-01 15:32:20.785573
1924	865	107	f	\N	Negative impacts not discussed.	\N	2026-04-01 15:32:20.785573
1925	865	108	f	\N	WIIFM for Finalizer not discussed.	\N	2026-04-01 15:32:20.785573
1926	865	109	f	\N	Mentor's role in motivations not discussed.	\N	2026-04-01 15:32:20.785573
1927	865	110	f	\N	Unclear impacts not discussed.	\N	2026-04-01 15:32:20.785573
1928	865	111	f	\N	Questions to uncover impact not discussed.	\N	2026-04-01 15:32:20.785573
1929	866	49	t	Final decision influencer, which was his dad.	Final authority identified.	\N	2026-04-01 15:32:20.785573
1930	866	50	f	\N	Proof of authority not discussed.	\N	2026-04-01 15:32:20.785573
1931	866	51	t	Jordan set up meetings with each key decision influencer.	Engagement plan exists.	\N	2026-04-01 15:32:20.785573
1932	866	52	f	\N	Post-approval steps not discussed.	\N	2026-04-01 15:32:20.785573
1933	866	53	f	\N	Finalizer's values not discussed.	\N	2026-04-01 15:32:20.785573
1934	866	54	f	\N	Message alignment not discussed.	\N	2026-04-01 15:32:20.785573
1935	866	55	f	\N	Access to Finalizer not discussed.	\N	2026-04-01 15:32:20.785573
1936	866	56	t	Final decision influencer, which was his dad.	Finalizer confirmed.	\N	2026-04-01 15:32:20.785573
1937	866	57	f	\N	Evidence of authority not discussed.	\N	2026-04-01 15:32:20.785573
1938	866	58	f	\N	Direct conversation with Finalizer not discussed.	\N	2026-04-01 15:32:20.785573
1939	866	59	f	\N	Positioning around values not discussed.	\N	2026-04-01 15:32:20.785573
1940	866	60	f	\N	Confirmation of timing not discussed.	\N	2026-04-01 15:32:20.785573
1941	866	61	f	\N	Unclear aspects not discussed.	\N	2026-04-01 15:32:20.785573
1942	866	62	f	\N	Post-approval process not discussed.	\N	2026-04-01 15:32:20.785573
1943	866	63	f	\N	Finalizer's priorities not discussed.	\N	2026-04-01 15:32:20.785573
1944	866	64	f	\N	Message alignment not discussed.	\N	2026-04-01 15:32:20.785573
1945	866	65	f	\N	Access to Finalizer not discussed.	\N	2026-04-01 15:32:20.785573
1946	866	66	f	\N	Confirmation of authority not discussed.	\N	2026-04-01 15:32:20.785573
1947	866	67	f	\N	Evidence of control not discussed.	\N	2026-04-01 15:32:20.785573
1948	866	68	f	\N	Plan to speak with Finalizer not discussed.	\N	2026-04-01 15:32:20.785573
1949	866	69	f	\N	Positioning around values not discussed.	\N	2026-04-01 15:32:20.785573
1950	866	70	f	\N	Unclear aspects not discussed.	\N	2026-04-01 15:32:20.785573
1951	867	85	t	The customer fit is right.	The transcript explicitly states customer fit is right.	\N	2026-04-01 15:40:10.00905
1952	867	86	f	\N	Not discussed	\N	2026-04-01 15:40:10.00905
1953	868	114	f	\N	Not discussed	\N	2026-04-01 15:40:10.00905
1954	869	73	t	Sales target true.	The transcript confirms sales target is true.	\N	2026-04-01 15:40:10.00905
1955	870	31	f	\N	Not discussed	\N	2026-04-01 15:40:10.00905
1956	871	140	t	Mentor true.	The transcript confirms mentor is true.	\N	2026-04-01 15:40:10.00905
1957	872	18	f	\N	Not discussed	\N	2026-04-01 15:40:10.00905
1958	873	2	t	Alternatives true.	The transcript confirms alternatives are true.	\N	2026-04-01 15:40:10.00905
1959	874	125	t	Hour solution ranking true.	The transcript confirms our solution ranking is true.	\N	2026-04-01 15:40:10.00905
1960	875	101	f	\N	Not discussed	\N	2026-04-01 15:40:10.00905
1961	876	49	t	Decision making process true.	The transcript confirms decision making process is true.	\N	2026-04-01 15:40:10.00905
1962	877	85	t	The customer fit is true.	Indicates leadership access.	\N	2026-04-01 16:00:03.99976
1963	877	86	t	The customer fit is true.	Implies understanding of differentiation.	\N	2026-04-01 16:00:03.99976
1964	877	87	t	The customer fit is true.	Shows real value alignment.	\N	2026-04-01 16:00:03.99976
1965	877	88	t	The customer fit is true.	Demonstrates appreciation for brand.	\N	2026-04-01 16:00:03.99976
1966	877	89	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1967	877	90	t	The customer fit is true.	Indicates openness and honesty.	\N	2026-04-01 16:00:03.99976
1968	877	91	t	The customer fit is true.	Fit criteria validated.	\N	2026-04-01 16:00:03.99976
1969	877	92	t	The customer fit is true.	Conversations confirm fit.	\N	2026-04-01 16:00:03.99976
1970	877	93	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1971	877	94	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1972	877	95	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1973	877	96	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1974	877	97	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1975	877	98	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1976	878	114	t	Trigger event and impact is true.	Indicates understanding of urgency.	\N	2026-04-01 16:00:03.99976
1977	878	115	t	Trigger event and impact is true.	Addresses real trigger event.	\N	2026-04-01 16:00:03.99976
1978	878	116	t	Trigger event and impact is true.	Identifies root cause.	\N	2026-04-01 16:00:03.99976
1979	878	117	t	Trigger event and impact is true.	Defines success measurement.	\N	2026-04-01 16:00:03.99976
1980	878	118	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1981	878	119	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1982	878	120	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1983	878	121	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1984	878	122	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1985	879	73	t	Sales target is true.	Confirms decision authority.	\N	2026-04-01 16:00:03.99976
1986	879	74	t	Sales target is true.	Indicates engagement with decision makers.	\N	2026-04-01 16:00:03.99976
1987	879	75	t	Sales target is true.	Clarifies purchase quantity and timing.	\N	2026-04-01 16:00:03.99976
1988	879	76	t	Sales target is true.	Confirms urgency.	\N	2026-04-01 16:00:03.99976
1989	879	77	t	Sales target is true.	Matches intended purchase.	\N	2026-04-01 16:00:03.99976
1990	879	78	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1991	879	79	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1992	879	80	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1993	879	81	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1994	879	82	f	\N	Not discussed.	\N	2026-04-01 16:00:03.99976
1995	880	31	f	\N	No evidence of Specifiers identified.	\N	2026-04-01 16:00:03.99976
1996	880	32	f	\N	No verification of Specifiers.	\N	2026-04-01 16:00:03.99976
1997	880	33	f	\N	No mention of external consultants.	\N	2026-04-01 16:00:03.99976
1998	880	34	f	\N	Specifications not discussed.	\N	2026-04-01 16:00:03.99976
1999	880	35	f	\N	Evaluation criteria not mentioned.	\N	2026-04-01 16:00:03.99976
2000	880	36	f	\N	Utilizers not identified.	\N	2026-04-01 16:00:03.99976
2001	880	37	f	\N	No confirmation of Utilizers.	\N	2026-04-01 16:00:03.99976
2002	880	38	f	\N	Utilizer concerns not addressed.	\N	2026-04-01 16:00:03.99976
2003	880	39	f	\N	Impact on Utilizers not discussed.	\N	2026-04-01 16:00:03.99976
2004	880	40	f	\N	Finalizer not identified.	\N	2026-04-01 16:00:03.99976
2005	880	41	f	\N	No engagement with Finalizer.	\N	2026-04-01 16:00:03.99976
2006	880	42	f	\N	Approval process not discussed.	\N	2026-04-01 16:00:03.99976
2007	880	43	f	\N	Finalizer's values not aligned.	\N	2026-04-01 16:00:03.99976
2008	880	44	f	\N	Timing and priorities not confirmed.	\N	2026-04-01 16:00:03.99976
2009	880	45	f	\N	No credible influence identified.	\N	2026-04-01 16:00:03.99976
2010	880	46	f	\N	Unclear aspects not resolved.	\N	2026-04-01 16:00:03.99976
2011	881	140	f	\N	No mentor identified.	\N	2026-04-01 16:00:03.99976
2012	881	141	f	\N	No gain/loss analysis.	\N	2026-04-01 16:00:03.99976
2013	881	142	f	\N	No strong belief shown.	\N	2026-04-01 16:00:03.99976
2014	881	143	f	\N	No mentor candidate named.	\N	2026-04-01 16:00:03.99976
2015	881	144	f	\N	No replacement identified.	\N	2026-04-01 16:00:03.99976
2016	881	145	f	\N	Hesitant individuals not identified.	\N	2026-04-01 16:00:03.99976
2017	881	146	f	\N	No mentor actions noted.	\N	2026-04-01 16:00:03.99976
2018	881	147	f	\N	Exclusivity not tested.	\N	2026-04-01 16:00:03.99976
2019	881	148	f	\N	No recent actions noted.	\N	2026-04-01 16:00:03.99976
2020	881	149	f	\N	No influence on others noted.	\N	2026-04-01 16:00:03.99976
2021	881	150	f	\N	No strategic shifts noted.	\N	2026-04-01 16:00:03.99976
2022	881	151	f	\N	No non-public info shared.	\N	2026-04-01 16:00:03.99976
2023	881	152	f	\N	Competition's mentor not identified.	\N	2026-04-01 16:00:03.99976
2024	881	153	f	\N	No secondary mentor.	\N	2026-04-01 16:00:03.99976
2025	881	154	f	\N	No next steps for mentor status.	\N	2026-04-01 16:00:03.99976
2026	881	155	f	\N	No request for mentoring.	\N	2026-04-01 16:00:03.99976
2027	881	156	f	\N	No risks identified.	\N	2026-04-01 16:00:03.99976
2028	881	157	f	\N	Project priority not ranked.	\N	2026-04-01 16:00:03.99976
2029	881	158	f	\N	No threat identified.	\N	2026-04-01 16:00:03.99976
2030	881	159	f	\N	No winners/losers identified.	\N	2026-04-01 16:00:03.99976
2031	881	160	f	\N	No alternatives discussed.	\N	2026-04-01 16:00:03.99976
2032	881	161	f	\N	No mentor assistance noted.	\N	2026-04-01 16:00:03.99976
2033	881	162	f	\N	No internal coaching identified.	\N	2026-04-01 16:00:03.99976
2034	882	18	t	Trigger priority is true.	Indicates high priority.	\N	2026-04-01 16:00:03.99976
2035	882	19	f	\N	Roles not discussed.	\N	2026-04-01 16:00:03.99976
2036	882	20	f	\N	Lower priority reasons not discussed.	\N	2026-04-01 16:00:03.99976
2037	882	21	f	\N	Finalizer's priority not confirmed.	\N	2026-04-01 16:00:03.99976
2038	882	22	f	\N	Proof not provided.	\N	2026-04-01 16:00:03.99976
2039	882	23	f	\N	Competing initiatives not discussed.	\N	2026-04-01 16:00:03.99976
2040	882	24	f	\N	Urgency increase not discussed.	\N	2026-04-01 16:00:03.99976
2041	882	25	f	\N	Mentor's role not mentioned.	\N	2026-04-01 16:00:03.99976
2042	882	26	f	\N	Internal urgency insights not shared.	\N	2026-04-01 16:00:03.99976
2043	882	27	f	\N	No further questions planned.	\N	2026-04-01 16:00:03.99976
2044	882	28	f	\N	Urgency questions not specified.	\N	2026-04-01 16:00:03.99976
2045	883	2	t	Alternative is true.	Alternatives identified.	\N	2026-04-01 16:00:03.99976
2046	883	3	f	\N	Perception not discussed.	\N	2026-04-01 16:00:03.99976
2047	883	4	f	\N	Inaction cost not discussed.	\N	2026-04-01 16:00:03.99976
2048	883	5	f	\N	Support for alternatives not identified.	\N	2026-04-01 16:00:03.99976
2049	883	6	f	\N	Advocacy reasons not discussed.	\N	2026-04-01 16:00:03.99976
2050	883	7	f	\N	Internal options not discussed.	\N	2026-04-01 16:00:03.99976
2051	883	8	f	\N	Political factors not discussed.	\N	2026-04-01 16:00:03.99976
2052	883	9	f	\N	Competitors not identified.	\N	2026-04-01 16:00:03.99976
2053	883	10	f	\N	Competitor strengths/weaknesses not discussed.	\N	2026-04-01 16:00:03.99976
2054	883	11	f	\N	Our strengths not discussed.	\N	2026-04-01 16:00:03.99976
2055	883	12	f	\N	Differentiation not discussed.	\N	2026-04-01 16:00:03.99976
2056	883	13	f	\N	Proof points not discussed.	\N	2026-04-01 16:00:03.99976
2057	883	14	f	\N	Mentor's role not mentioned.	\N	2026-04-01 16:00:03.99976
2058	883	15	f	\N	No further questions planned.	\N	2026-04-01 16:00:03.99976
2059	884	125	f	\N	Solution ranking not confirmed.	\N	2026-04-01 16:00:03.99976
2060	884	126	f	\N	No evidence provided.	\N	2026-04-01 16:00:03.99976
2061	884	127	f	\N	Differentiators not discussed.	\N	2026-04-01 16:00:03.99976
2062	884	128	f	\N	Finalizer's value not discussed.	\N	2026-04-01 16:00:03.99976
2063	884	129	f	\N	Competitor preference not identified.	\N	2026-04-01 16:00:03.99976
2064	884	130	f	\N	Advantages not discussed.	\N	2026-04-01 16:00:03.99976
2065	884	131	f	\N	No response to challenges.	\N	2026-04-01 16:00:03.99976
2066	884	132	f	\N	Price vs outcomes not reframed.	\N	2026-04-01 16:00:03.99976
2067	884	133	f	\N	Mentor's role not mentioned.	\N	2026-04-01 16:00:03.99976
2068	884	134	f	\N	Success definition not discussed.	\N	2026-04-01 16:00:03.99976
2069	884	135	f	\N	Outcomes not prioritized.	\N	2026-04-01 16:00:03.99976
2070	884	136	f	\N	Ranking status not discussed.	\N	2026-04-01 16:00:03.99976
2071	884	137	f	\N	No further questions planned.	\N	2026-04-01 16:00:03.99976
2072	885	101	t	Individual impact is true.	Personal impact identified.	\N	2026-04-01 16:00:03.99976
2073	885	102	f	\N	Understanding not confirmed.	\N	2026-04-01 16:00:03.99976
2074	885	103	f	\N	Connection not discussed.	\N	2026-04-01 16:00:03.99976
2075	885	104	f	\N	Competition's impact not discussed.	\N	2026-04-01 16:00:03.99976
2076	885	105	f	\N	Unique WIIFM not identified.	\N	2026-04-01 16:00:03.99976
2077	885	106	f	\N	Positive impacts not leveraged.	\N	2026-04-01 16:00:03.99976
2078	885	107	f	\N	Negative impacts not addressed.	\N	2026-04-01 16:00:03.99976
2079	885	108	f	\N	WIIFM for Finalizer not identified.	\N	2026-04-01 16:00:03.99976
2080	885	109	f	\N	Mentor's role not mentioned.	\N	2026-04-01 16:00:03.99976
2081	885	110	f	\N	No further questions planned.	\N	2026-04-01 16:00:03.99976
2082	885	111	f	\N	No questions specified.	\N	2026-04-01 16:00:03.99976
2083	886	49	t	Decision making process is true.	Final authority identified.	\N	2026-04-01 16:00:03.99976
2084	886	50	t	Decision making process is true.	Authority confirmed.	\N	2026-04-01 16:00:03.99976
2085	886	51	t	Decision making process is true.	Engagement confirmed.	\N	2026-04-01 16:00:03.99976
2086	886	52	t	Decision making process is true.	Approval process clear.	\N	2026-04-01 16:00:03.99976
2087	886	53	t	Decision making process is true.	Finalizer's values aligned.	\N	2026-04-01 16:00:03.99976
2088	886	54	f	\N	Message alignment not discussed.	\N	2026-04-01 16:00:03.99976
2089	886	55	f	\N	Influence access not discussed.	\N	2026-04-01 16:00:03.99976
2090	886	56	f	\N	Finalizer not confirmed.	\N	2026-04-01 16:00:03.99976
2091	886	57	f	\N	Authority evidence not provided.	\N	2026-04-01 16:00:03.99976
2092	886	58	f	\N	No engagement plan.	\N	2026-04-01 16:00:03.99976
2093	886	59	f	\N	Positioning not discussed.	\N	2026-04-01 16:00:03.99976
2094	886	60	f	\N	Timing and priorities not confirmed.	\N	2026-04-01 16:00:03.99976
2095	886	61	f	\N	No further questions planned.	\N	2026-04-01 16:00:03.99976
2096	886	62	f	\N	Approval process not detailed.	\N	2026-04-01 16:00:03.99976
2097	886	63	f	\N	Finalizer's values not aligned.	\N	2026-04-01 16:00:03.99976
2098	886	64	f	\N	Message alignment not discussed.	\N	2026-04-01 16:00:03.99976
2099	886	65	f	\N	Influence access not discussed.	\N	2026-04-01 16:00:03.99976
2100	886	66	f	\N	Authority not confirmed.	\N	2026-04-01 16:00:03.99976
2101	886	67	f	\N	Control evidence not provided.	\N	2026-04-01 16:00:03.99976
2102	886	68	f	\N	No engagement plan.	\N	2026-04-01 16:00:03.99976
2103	886	69	f	\N	Positioning not discussed.	\N	2026-04-01 16:00:03.99976
2104	886	70	f	\N	No further questions planned.	\N	2026-04-01 16:00:03.99976
2105	887	85	t	The customer fate is true.	The transcript explicitly states customer fit is true.	\N	2026-04-01 16:31:12.562289
2106	887	86	f	\N	Not discussed	\N	2026-04-01 16:31:12.562289
2107	888	114	f	\N	The transcript states trigger event and impact is false.	\N	2026-04-01 16:31:12.562289
2108	889	73	t	Sales target true.	The transcript explicitly states sales target is true.	\N	2026-04-01 16:31:12.562289
2109	890	31	f	\N	The transcript states decision influencer is false.	\N	2026-04-01 16:31:12.562289
2110	891	140	t	Mentor true.	The transcript explicitly states mentor is true.	\N	2026-04-01 16:31:12.562289
2111	892	18	t	Trigger priority true.	The transcript explicitly states trigger priority is true.	\N	2026-04-01 16:31:12.562289
2112	893	2	t	Alternatives true.	The transcript explicitly states alternatives are true.	\N	2026-04-01 16:31:12.562289
2113	894	125	t	Our solution ranking true.	The transcript explicitly states our solution ranking is true.	\N	2026-04-01 16:31:12.562289
2114	895	101	t	Individual impact true.	The transcript explicitly states individual impact is true.	\N	2026-04-01 16:31:12.562289
2115	896	49	t	Decision making process true.	The transcript explicitly states decision making process is true.	\N	2026-04-01 16:31:12.562289
2116	897	85	t	The customer fit is true	The transcript explicitly states customer fit is true.	\N	2026-04-01 18:44:24.186953
2117	897	86	f	\N	No specific evidence of understanding and valuing differentiation.	\N	2026-04-01 18:44:24.186953
2118	898	114	f	\N	No evidence of trigger event or measurable outcomes.	\N	2026-04-01 18:44:24.186953
2119	899	73	t	sales target true	The transcript explicitly states sales target is true.	\N	2026-04-01 18:44:24.186953
2120	900	31	t	decision influencers true	The transcript explicitly states decision influencers are true.	\N	2026-04-01 18:44:24.186953
2121	901	140	t	mentor true	The transcript explicitly states mentor is true.	\N	2026-04-01 18:44:24.186953
2122	902	18	t	trigger priority true	The transcript explicitly states trigger priority is true.	\N	2026-04-01 18:44:24.186953
2123	903	2	t	alternatives true	The transcript explicitly states alternatives are true.	\N	2026-04-01 18:44:24.186953
2124	904	125	t	power solution ranking true	The transcript explicitly states power solution ranking is true.	\N	2026-04-01 18:44:24.186953
2125	905	101	t	individual impact yes	The transcript explicitly states individual impact is yes.	\N	2026-04-01 18:44:24.186953
2126	906	49	t	decision making process true	The transcript explicitly states decision making process is true.	\N	2026-04-01 18:44:24.186953
2127	907	85	t	Customer fit is true.	The transcript states customer fit is true.	\N	2026-04-06 10:01:35.509231
2128	907	86	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2129	907	87	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2130	907	88	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2131	907	89	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2132	907	90	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2133	907	91	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2134	907	92	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2135	907	93	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2136	907	94	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2137	907	95	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2138	907	96	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2139	907	97	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2140	907	98	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2141	908	114	t	Trigger event and impact is true.	The transcript states trigger event and impact is true.	\N	2026-04-06 10:01:35.509231
2142	908	115	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2143	908	116	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2144	908	117	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2145	908	118	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2146	908	119	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2147	908	120	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2148	908	121	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2149	908	122	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2150	909	73	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2151	909	74	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2152	909	75	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2153	909	76	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2154	909	77	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2155	909	78	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2156	909	79	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2157	909	80	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2158	909	81	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2159	909	82	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2160	910	31	t	Decision influencer is true.	The transcript states decision influencer is true.	\N	2026-04-06 10:01:35.509231
2161	910	32	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2162	910	33	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2163	910	34	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2164	910	35	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2165	910	36	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2166	910	37	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2167	910	38	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2168	910	39	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2169	910	40	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2170	910	41	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2171	910	42	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2172	910	43	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2173	910	44	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2174	910	45	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2175	910	46	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2176	911	140	t	Mentor is true.	The transcript states mentor is true.	\N	2026-04-06 10:01:35.509231
2177	911	141	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2178	911	142	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2179	911	143	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2180	911	144	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2181	911	145	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2182	911	146	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2183	911	147	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2184	911	148	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2185	911	149	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2186	911	150	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2187	911	151	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2188	911	152	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2189	911	153	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2190	911	154	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2191	911	155	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2192	911	156	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2193	911	157	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2194	911	158	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2195	911	159	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2196	911	160	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2197	911	161	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2198	911	162	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2199	912	18	t	Trigger priority is true.	The transcript states trigger priority is true.	\N	2026-04-06 10:01:35.509231
2200	912	19	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2201	912	20	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2202	912	21	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2203	912	22	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2204	912	23	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2205	912	24	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2206	912	25	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2207	912	26	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2208	912	27	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2209	912	28	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2210	913	2	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2211	913	3	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2212	913	4	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2213	913	5	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2214	913	6	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2215	913	7	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2216	913	8	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2217	913	9	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2218	913	10	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2219	913	11	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2220	913	12	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2221	913	13	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2222	913	14	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2223	913	15	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2224	914	125	t	Our solution ranking is true.	The transcript states our solution ranking is true.	\N	2026-04-06 10:01:35.509231
2225	914	126	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2226	914	127	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2227	914	128	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2228	914	129	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2229	914	130	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2230	914	131	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2231	914	132	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2232	914	133	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2233	914	134	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2234	914	135	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2235	914	136	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2236	914	137	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2237	915	101	t	Individual impact is true.	The transcript states individual impact is true.	\N	2026-04-06 10:01:35.509231
2238	915	102	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2239	915	103	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2240	915	104	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2241	915	105	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2242	915	106	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2243	915	107	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2244	915	108	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2245	915	109	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2246	915	110	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2247	915	111	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2248	916	49	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2249	916	50	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2250	916	51	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2251	916	52	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2252	916	53	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2253	916	54	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2254	916	55	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2255	916	56	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2256	916	57	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2257	916	58	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2258	916	59	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2259	916	60	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2260	916	61	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2261	916	62	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2262	916	63	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2263	916	64	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2264	916	65	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2265	916	66	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2266	916	67	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2267	916	68	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2268	916	69	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
2269	916	70	f	\N	Not discussed	\N	2026-04-06 10:01:35.509231
\.


--
-- Data for Name: session_responses; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.session_responses (id, session_id, item_id, ai_reasoning, created_at, updated_at, ai_answer, user_answer, was_changed, score) FROM stdin;
847	87	134	Manual entry by user	2026-03-31 15:36:32.169952	2026-03-31 15:36:32.170006	t	\N	f	10
848	87	135	Manual entry by user	2026-03-31 15:36:32.170012	2026-03-31 15:36:32.170015	t	\N	f	10
849	87	136	Manual entry by user	2026-03-31 15:36:32.170017	2026-03-31 15:36:32.17002	t	\N	f	10
850	87	137	Manual entry by user	2026-03-31 15:36:32.170023	2026-03-31 15:36:32.170025	t	\N	f	10
851	87	138	Manual entry by user	2026-03-31 15:36:32.170028	2026-03-31 15:36:32.17003	t	\N	f	10
852	87	139	Manual entry by user	2026-03-31 15:36:32.170033	2026-03-31 15:36:32.170035	t	\N	f	10
853	87	140	Manual entry by user	2026-03-31 15:36:32.170038	2026-03-31 15:36:32.170041	t	\N	f	10
854	87	141	Manual entry by user	2026-03-31 15:36:32.170044	2026-03-31 15:36:32.170047	t	\N	f	10
855	87	142	Manual entry by user	2026-03-31 15:36:32.170049	2026-03-31 15:36:32.170052	t	\N	f	10
856	87	143	Manual entry by user	2026-03-31 15:36:32.170054	2026-03-31 15:36:32.170057	t	\N	f	10
857	89	134	Multiple decision influencers were engaged, and they appreciate the brand and value.	2026-04-01 15:32:20.442251	2026-04-01 15:32:20.442261	t	\N	f	10
858	89	135	The trigger event and desired outcomes are clearly identified.	2026-04-01 15:32:22.840709	2026-04-01 15:32:22.840736	t	\N	f	10
859	89	136	Sales target details are clearly understood and aligned.	2026-04-01 15:32:23.991696	2026-04-01 15:32:23.991707	t	\N	f	10
860	89	138	All key Decision Influencers have been identified and engaged.	2026-04-01 15:32:25.145708	2026-04-01 15:32:25.145715	t	\N	f	10
861	89	139	A Mentor, Jordan, has been identified and is actively supporting the sales process.	2026-04-01 15:32:26.359102	2026-04-01 15:32:26.359112	t	\N	f	10
862	89	140	The project is a priority for all key Decision Influencers.	2026-04-01 15:32:27.878392	2026-04-01 15:32:27.878399	t	\N	f	10
863	89	141	Alternatives have been identified and strategies developed.	2026-04-01 15:32:29.087219	2026-04-01 15:32:29.087228	t	\N	f	10
864	89	142	Our solution is ranked highly and uniquely solves the Trigger Event.	2026-04-01 15:32:30.215596	2026-04-01 15:32:30.215605	t	\N	f	10
865	89	143	Individual impacts have been identified for key Decision Influencers.	2026-04-01 15:32:31.429867	2026-04-01 15:32:31.429874	t	\N	f	10
866	89	137	Steps in the Decision Making Process are identified and funding is verified.	2026-04-01 15:32:32.488669	2026-04-01 15:32:32.488678	t	\N	f	10
867	90	134	The transcript confirms customer fit is right.	2026-04-01 15:40:09.7664	2026-04-01 15:40:09.766413	t	\N	f	10
868	90	135	The transcript indicates trigger event and impact is wrong.	2026-04-01 15:40:11.563101	2026-04-01 15:40:11.56311	f	\N	f	0
869	90	136	Sales target is confirmed as true in the transcript.	2026-04-01 15:40:12.466377	2026-04-01 15:40:12.466385	t	\N	f	10
870	90	138	Decision influencers are marked as false in the transcript.	2026-04-01 15:40:13.154373	2026-04-01 15:40:13.154379	f	\N	f	0
871	90	139	Mentor is confirmed as true in the transcript.	2026-04-01 15:40:13.829253	2026-04-01 15:40:13.829261	t	\N	f	10
872	90	140	Trigger priority is marked as false in the transcript.	2026-04-01 15:40:14.565431	2026-04-01 15:40:14.565439	f	\N	f	0
873	90	141	Alternatives are confirmed as true in the transcript.	2026-04-01 15:40:15.237314	2026-04-01 15:40:15.237321	t	\N	f	10
874	90	142	Our solution ranking is confirmed as true in the transcript.	2026-04-01 15:40:15.976876	2026-04-01 15:40:15.976885	t	\N	f	10
875	90	143	Individual impact is marked as false in the transcript.	2026-04-01 15:40:16.765174	2026-04-01 15:40:16.765183	f	\N	f	0
876	90	137	Decision making process is confirmed as true in the transcript.	2026-04-01 15:40:17.452582	2026-04-01 15:40:17.45259	t	\N	f	10
877	93	134	The transcript states 'customer fit is true', indicating all criteria are met.	2026-04-01 16:00:03.740297	2026-04-01 16:00:03.740308	t	\N	f	10
878	93	135	The transcript states 'trigger event and impact is true', indicating understanding of urgency and outcomes.	2026-04-01 16:00:05.52167	2026-04-01 16:00:05.521678	t	\N	f	10
879	93	136	The transcript states 'sales target is true', indicating clarity on purchase plans.	2026-04-01 16:00:06.414982	2026-04-01 16:00:06.414989	t	\N	f	10
880	93	138	The transcript states 'decision influencer is false', indicating lack of engagement with key influencers.	2026-04-01 16:00:07.308312	2026-04-01 16:00:07.308321	f	\N	f	0
881	93	139	The transcript states 'mentor is false', indicating no mentor development.	2026-04-01 16:00:08.219799	2026-04-01 16:00:08.219805	f	\N	f	0
882	93	140	The transcript states 'trigger priority is true', indicating validated urgency across influencers.	2026-04-01 16:00:09.130132	2026-04-01 16:00:09.13014	t	\N	f	10
883	93	141	The transcript states 'alternative is true', indicating identification of alternatives.	2026-04-01 16:00:10.066308	2026-04-01 16:00:10.066317	t	\N	f	10
884	93	142	The transcript states 'hour solution ranking is false', indicating poor ranking.	2026-04-01 16:00:10.882112	2026-04-01 16:00:10.882119	f	\N	f	0
885	93	143	The transcript states 'individual impact is true', indicating understanding of personal impacts.	2026-04-01 16:00:11.809756	2026-04-01 16:00:11.809763	t	\N	f	10
886	93	137	The transcript states 'decision making process is true', indicating clarity on decision steps.	2026-04-01 16:00:12.48554	2026-04-01 16:00:12.485549	t	\N	f	10
887	94	134	The transcript indicates that the customer fit is true.	2026-04-01 16:31:12.353107	2026-04-01 16:31:12.353203	t	\N	f	10
888	94	135	The transcript indicates that the trigger event and impact is false.	2026-04-01 16:31:13.610391	2026-04-01 16:31:13.610415	f	\N	f	0
889	94	136	The transcript indicates that the sales target is true.	2026-04-01 16:31:14.526182	2026-04-01 16:31:14.526191	t	\N	f	10
890	94	138	The transcript indicates that the decision influencer is false.	2026-04-01 16:31:15.003141	2026-04-01 16:31:15.003152	f	\N	f	0
891	94	139	The transcript indicates that the mentor is true.	2026-04-01 16:31:15.487747	2026-04-01 16:31:15.487756	t	\N	f	10
892	94	140	The transcript indicates that the trigger priority is true.	2026-04-01 16:31:16.063215	2026-04-01 16:31:16.063224	t	\N	f	10
893	94	141	The transcript indicates that alternatives are true.	2026-04-01 16:31:16.600876	2026-04-01 16:31:16.600884	t	\N	f	10
894	94	142	The transcript indicates that our solution ranking is true.	2026-04-01 16:31:19.999553	2026-04-01 16:31:19.999561	t	\N	f	10
895	94	143	The transcript indicates that individual impact is true.	2026-04-01 16:31:20.507033	2026-04-01 16:31:20.507041	t	\N	f	10
896	94	137	The transcript indicates that the decision making process is true.	2026-04-01 16:31:20.99907	2026-04-01 16:31:20.999078	t	\N	f	10
897	95	134	The transcript confirms customer fit is true.	2026-04-01 18:44:24.073888	2026-04-01 18:44:24.07389	t	\N	f	10
898	95	135	The transcript states trigger event and impact are false.	2026-04-01 18:44:25.231156	2026-04-01 18:44:25.231158	f	\N	f	0
899	95	136	The transcript confirms sales target is true.	2026-04-01 18:44:25.914606	2026-04-01 18:44:25.914608	t	\N	f	10
900	95	138	The transcript confirms decision influencers are true.	2026-04-01 18:44:26.370974	2026-04-01 18:44:26.370976	t	\N	f	10
901	95	139	The transcript confirms mentor is true.	2026-04-01 18:44:26.827182	2026-04-01 18:44:26.827184	t	\N	f	10
902	95	140	The transcript confirms trigger priority is true.	2026-04-01 18:44:27.284172	2026-04-01 18:44:27.284174	t	\N	f	10
903	95	141	The transcript confirms alternatives are true.	2026-04-01 18:44:27.740836	2026-04-01 18:44:27.740839	t	\N	f	10
904	95	142	The transcript confirms power solution ranking is true.	2026-04-01 18:44:28.197469	2026-04-01 18:44:28.197472	t	\N	f	10
905	95	143	The transcript confirms individual impact is yes.	2026-04-01 18:44:28.653016	2026-04-01 18:44:28.653019	t	\N	f	10
906	95	137	The transcript confirms decision making process is true.	2026-04-01 18:44:29.110282	2026-04-01 18:44:29.110284	t	\N	f	10
907	96	134	The transcript indicates the customer fit is true.	2026-04-06 10:01:35.39427	2026-04-06 10:01:35.394273	t	\N	f	10
912	96	140	The transcript indicates trigger priority is true.	2026-04-06 10:01:39.539093	2026-04-06 10:01:39.539095	t	\N	f	10
913	96	141	The transcript indicates alternatives are false.	2026-04-06 10:01:40.226012	2026-04-06 10:01:40.226015	f	\N	f	0
914	96	142	The transcript indicates our solution ranking is true.	2026-04-06 10:01:40.694814	2026-04-06 10:01:40.694817	t	\N	f	10
915	96	143	The transcript indicates individual impact is true.	2026-04-06 10:01:41.381787	2026-04-06 10:01:41.38179	t	\N	f	10
916	96	137	The transcript indicates the decision-making process is false.	2026-04-06 10:01:41.840888	2026-04-06 10:01:41.84089	f	\N	f	0
909	96	136	The transcript indicates the sales target is false.	2026-04-06 10:01:37.475524	2026-04-06 10:03:39.424723	f	t	t	10
908	96	135	The transcript indicates the trigger event and impact is true.	2026-04-06 10:01:36.787884	2026-04-17 20:08:42.359072	t	f	t	0
910	96	138	The transcript indicates decision influencers are true.	2026-04-06 10:01:38.162589	2026-04-17 20:08:59.784083	t	f	t	0
911	96	139	The transcript indicates mentor is true.	2026-04-06 10:01:38.851006	2026-04-17 20:09:08.805855	t	f	t	0
927	99	134	Manual entry by user	2026-05-07 18:48:42.598305	2026-05-07 18:48:42.598308	t	\N	f	10
928	99	135	Manual entry by user	2026-05-07 18:48:42.598309	2026-05-07 18:48:42.598309	t	\N	f	10
929	99	136	Manual entry by user	2026-05-07 18:48:42.59831	2026-05-07 18:48:42.59831	t	\N	f	10
930	99	139	Manual entry by user	2026-05-07 18:48:42.598311	2026-05-07 18:48:42.598311	t	\N	f	10
931	99	140	Manual entry by user	2026-05-07 18:48:42.598311	2026-05-07 18:48:42.598312	t	\N	f	10
932	99	141	Manual entry by user	2026-05-07 18:48:42.598312	2026-05-07 18:48:42.598312	t	\N	f	10
933	100	134	Manual entry by user	2026-05-26 15:53:37.324445	2026-05-26 15:53:37.324449	t	\N	f	10
934	100	135	Manual entry by user	2026-05-26 15:53:37.324449	2026-05-26 15:53:37.324449	f	\N	f	0
935	100	136	Manual entry by user	2026-05-26 15:53:37.32445	2026-05-26 15:53:37.32445	t	\N	f	10
936	100	137	Manual entry by user	2026-05-26 15:53:37.32445	2026-05-26 15:53:37.324451	f	\N	f	0
937	100	138	Manual entry by user	2026-05-26 15:53:37.324451	2026-05-26 15:53:37.324451	t	\N	f	10
938	100	139	Manual entry by user	2026-05-26 15:53:37.324451	2026-05-26 15:53:37.324452	f	\N	f	0
939	100	140	Manual entry by user	2026-05-26 15:53:37.324452	2026-05-26 15:53:37.324452	f	\N	f	0
940	100	141	Manual entry by user	2026-05-26 15:53:37.324453	2026-05-26 15:53:37.324453	f	\N	f	0
941	100	142	Manual entry by user	2026-05-26 15:53:37.324453	2026-05-26 15:53:37.324453	f	\N	f	0
942	100	143	Manual entry by user	2026-05-26 15:53:37.324454	2026-05-26 15:53:37.324454	f	\N	f	0
943	101	134	Manual entry by user	2026-06-09 12:44:42.405746	2026-06-09 12:44:42.405758	t	\N	f	10
944	101	135	Manual entry by user	2026-06-09 12:44:42.405763	2026-06-09 12:44:42.405766	f	\N	f	0
945	101	136	Manual entry by user	2026-06-09 12:44:42.405769	2026-06-09 12:44:42.405771	t	\N	f	10
946	101	137	Manual entry by user	2026-06-09 12:44:42.405774	2026-06-09 12:44:42.405777	t	\N	f	10
947	101	138	Manual entry by user	2026-06-09 12:44:42.40578	2026-06-09 12:44:42.405782	f	\N	f	0
948	101	139	Manual entry by user	2026-06-09 12:44:42.405785	2026-06-09 12:44:42.405788	t	\N	f	10
949	101	140	Manual entry by user	2026-06-09 12:44:42.40579	2026-06-09 12:44:42.405792	t	\N	f	10
950	101	141	Manual entry by user	2026-06-09 12:44:42.405795	2026-06-09 12:44:42.405797	t	\N	f	10
951	101	142	Manual entry by user	2026-06-09 12:44:42.4058	2026-06-09 12:44:42.405802	f	\N	f	0
952	101	143	Manual entry by user	2026-06-09 12:44:42.405805	2026-06-09 12:44:42.405807	t	\N	f	10
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sessions (id, user_id, customer_name, opportunity_name, decision_influencer, status, submitted_at, completed_at, created_at, updated_at, session_mode, deal_stage) FROM stdin;
87	14	Acme Enterprise	Q4 Enterprise Deal	John Smith (VP Sales)	COMPLETED	2026-03-31 15:36:36.624363	\N	2026-03-31 14:50:09.308786	2026-03-31 15:36:36.627576	MANUAL	PROPOSAL
89	14	Tester	Test	Muhammad Farooq	COMPLETED	2026-04-01 15:33:08.344685	\N	2026-04-01 15:27:54.068366	2026-04-01 15:33:08.346113	AUDIO	PROPOSAL
90	14	Test 2	Test 2	Test 2 Farooq	COMPLETED	2026-04-01 15:44:52.836579	\N	2026-04-01 15:38:18.161481	2026-04-01 15:44:52.847068	AUDIO	active
93	14	Farooq Testing	Test	Muhammad Farooq	COMPLETED	2026-04-01 16:13:36.410968	\N	2026-04-01 15:57:23.062392	2026-04-01 16:13:36.418818	AUDIO	proposal
94	14	Test 3	Testing 3	Muhammad Farooq - T3	COMPLETED	2026-04-01 16:31:50.655342	\N	2026-04-01 16:29:35.97152	2026-04-01 16:31:50.656721	AUDIO	active
95	14	Acme Corporation	Q2 Software Implementation	John Smith (VP Sales)	COMPLETED	2026-04-01 18:44:45.114001	\N	2026-04-01 18:42:58.49822	2026-04-01 18:44:45.115662	AUDIO	proposal
96	14	Acme Corporation	Q2 Software Implementation	Muhammad Farooq	COMPLETED	2026-04-06 10:03:11.981938	\N	2026-04-06 09:59:21.43249	2026-04-06 10:09:18.888369	AUDIO	lost
99	14	Test	Test	Test	COMPLETED	2026-05-07 18:48:47.69249	\N	2026-05-07 18:41:46.332117	2026-05-07 18:48:47.693889	MANUAL	active
100	14	Test 2	Test 2		COMPLETED	2026-05-26 15:53:41.888895	\N	2026-05-26 15:52:26.157951	2026-05-26 15:53:41.889939	MANUAL	\N
101	14	Farooq Testing	Q2 Software Implementation	Hafiz Fahad	COMPLETED	2026-06-09 12:44:48.431437	\N	2026-06-08 19:30:43.779675	2026-06-09 12:44:48.439623	MANUAL	active
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teams (id, organization_id, name, is_active, created_at, updated_at) FROM stdin;
4	5	Sales Testers	t	2025-12-05 15:12:44.114097	2025-12-05 15:12:44.114103
5	5	Test team	t	2026-03-04 21:22:28.275602	2026-03-04 21:22:28.27561
6	5	Muhammad's Lovable	t	2026-04-17 18:24:12.746021	2026-04-17 18:24:12.746025
\.


--
-- Data for Name: transcripts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.transcripts (id, session_id, text, language, duration, words_count, transcribed_at, processing_time, openai_request_id, created_at, updated_at) FROM stdin;
45	89	December 2nd, 2025, the time is 8.58 a.m. and I am sitting in front of Kansas City Deck Supply in Kansas City, Missouri. Today the sales checklist scores a customer fit, yes. We have met with multiple decision influencers over the last six months. They have given us plenty of time and had open and honest communication with us. They appreciate the brand Deck Pro Prestige and the value not only the product provides but the service that we are providing as well. This is well above the minimum size. This is an annual potential of almost $1 million of incremental revenue. influencers from the key decision influencers, the final decision maker, and even specifiers and utilizers including contractors that we have been able to meet with all show interest and appreciate the brand and the value. This opportunity is worth my time so the customer fit scores a yes. Trigger event, we do know what is causing them to want to make a change. They are tired of a product in the market place that they go out and create demand only for the vendor community to go out and set up additional dealerships across the GMA that they cover. We understand that they don't like that. They don't like creating a lot of demand and losing it to go to a competition. The target, well before I go to the target, the trigger event is a yes so we do know what is causing them to want to make a decision. The sales target, we do know what they are planning on buying and how much and when. As we move into December, we know that the way they purchase this product and make changes happens this time of year. In December, it's one of the slower months, it's ending the business year as they begin to plan and start thinking about the next year. So if there's any decisions to be made, it's now and we recognized that six months ago when we started talking about this. Initially they will buy a full truckload of product ranging about $150,000 and they will make that purchase by the end of December. So we do understand the sales target and that would score a yes on the checklist. For decision making process, we do know what's important to them in their decision making process. We've learned all of the things that are important to them from the railing style and choice. We understand that not only the product needs to be a good finish and well built, but ease of installation. We pulled in their contractors so that way they could have a handle and input on how it installs versus that of what they've been selling and they have confirmed that this is a product that they can work with. They understand that the impact of switching this operationally means they have to do work in the operation, they have to bring in SKUs and they want to know that our packaging is as good, if not better. Our labeling is easy to read and the pallets will fit on their racks that they have. They have asked for an Excel spreadsheet to be able to delay the UPCs, excuse me, input the labels of the UPCs into their computer systems. Additionally, they want to know about back ends and rebates and we've learned that they have a current 4% back end rebate coming annually from their current supplier. They also want to be able to have warehouse capabilities to purchase the stocked colors, excuse me, the non-stock colors, which would be white and maple cream at a discounted rate, but they would know they will not get the same prices when they buy full truckloads on the black and the bronze product. We know that there is plenty of funding and that they have good standing credit and they can pay for the product in the terms that will be defined in that 60 days. So for decision making process, we do believe we understand their decision making criteria and again, we understand the timing, we understand what's important to them and we know that the project can get funding, so we would say yes. We do have a yes on decision making process. We did get to meet with multiple decision influencers across their entire organization from their warehouse folks, the ones that would be unloading our trucks to the warehouse pullers. We met with those folks to understand what's important to them and the labels as well as the skid quantities. Then we moved up to the customer service inside sales folks. We understand how their sales people, excuse me, how their customers come in and talk to them about railing projects and we have trained and got their feedback on not only our product, what their expectations are, we've met with their outside sales people to determine what's important to them and we've been able to again meet with contractors to talk to them about the product itself. We've met with the purchasing agent, we've met with managers and we've met with ownership. So we have met with all decision influencers and engaged them all. So we would say for number five decision influencers, that is a yes as well. Number six, mentor. We do have a mentor. We have developed a relationship with an internal person within their organization who's really pulling for us. His name is Jordan. He wants to have a product that his sales team can go out and not have to worry about creating demand and then us go and try to set up another dealer when a competitor comes to us. We believe we have some upward opportunity with that that we can tailor into our full proposal and Jordan appreciates that and he has been doing things for us with his brothers, which is part of the ownership in the team, to allow them to come on board and creating opportunities for us to get to know them as well. And so specifically we asked Jordan to set up meetings with each of the key decision influencers as well as the final decision influencer, which was his dad, and he did that for us. So we believe that we do have a mentor established and that is Jordan and he's been able to make things happen with other decision influencers. Number seven, we understand the trigger priority and where the priorities ally and believe it or not at this time, six months later, we have an alignment in all priorities. This project is a priority not only at the final decision making level with the dad, but also the brothers, which is the CFO, the vice president of operations, the vice president of sales, the purchasing agent, the sales team, and the warehouses and several of their top contractors. So we do believe this is a trigger priority for them. Alternatives, we have identified all the alternatives that exist out there. Number one, the do nothing, keep the same product that they have and keep doing things the way they have. We've also learned that they are not evaluating another product outside of ours because they already stock so many different products. They're going to continue to stock other products, but the one they're looking to replace and do more, move more business away from is Westbury and Fortress Railing. They're not going to get rid of them, but they want to have a rail system and a solution that we offer. So we realize that our alternative here is really do nothing, but we do believe we understand the alternatives completely, and so we would say yes on this. So as of right now, that's eight out of 10. So 80 out of 100, we move on to our solution ranking. We believe we know what the trigger event is, and we have a very good inclination that our solution is going to solve their problem. We believe that our solution ranks right up there, far ahead of the alternative of doing nothing. And so therefore, we believe that that score is a 10 as well, bringing us to 90 out of 100 and a yes on number nine solution ranking, followed by number 10. And this is the one that was probably the most fun at this stage of the game, was learning about what's in it for each of the individuals. And we did get to learn that one of the biggest benefits of what's in it for many of them is the idea that we have been toting of providing some exclusivity, number one. And number two, a consignment program. It allows to remove the risk, where we will put this product in on consignment and bill them every month after they ship. Now that's going to be some legwork on our, but we understand with that, coupled with a exclusivity in the market, they feel like they will have a product that is exclusive to them and a partnership that's exclusive to them, and they don't have that with anybody else. So professionally, they do like that. Personally, they have worked with our company for a long time. They understand our ADI advantage, the value proposition, and they want to do more with our company, so they say. So I believe that we've identified at all levels and the key decision influencers, the final decision influencer, as well as many of the other decision influencers, how they will be personally impacted all the way down to the warehouse, from the way they unload the product and how that would come in on units of 64, and the way they're palletized and how that will make them, their jobs easier. So they say, they understand from a customer service standpoint and a sales standpoint that they will have the support that we offer, and that impacts their job because they don't have to now deal with a phone call trying to figure things themselves out. They know that they can trust our salesperson there to make things happen for them. So with that being said, we believe, yes, that score says 10 out of 10, so we've got a score of 100. The next steps that we're ready to do is we're ready to make a proposal, and we're going to send an appointment, which they're expecting, anticipating, which they have been patient with us as we've worked our process, and we are going to set a time to meet with them and make a formalized proposal and review not only the things that we learned, the problem that they have, the trigger event that persists and how we can solve it for them, and then we will walk our solution for all the way through in our proposal. It'll be a written proposal that we leave and give to, excuse me, leave with them. We will not read it verbatim, but we will hit the highlights when we make the proposal, and then when we leave there, we will ask for the business and we will confirm next steps. So this is a 10 out of a 10 ready for proposal, and we have our final item remaining, and that's what to do. Let's make the proposal, and we will make that on December 17th of this month. So that's it.	english	692.2999877929688	1909	\N	30	\N	2026-04-01 15:31:04.509048	2026-04-01 15:31:04.509057
46	90	The customer fit is right. Trigger event and impact is wrong. Sales target true. Decision making process true. Decision influencers false. Mentor true. Alternatives true. Trigger priority false. Hour solution ranking true. Individual impact false.	english	24.239999771118164	35	\N	30	\N	2026-04-01 15:39:45.339579	2026-04-01 15:39:45.339589
47	93	The customer fit is true. Trigger event and impact is true. Sales target is true. Decision making process is true. Decision influencer is false. Mentor is false. Trigger priority is true. Alternative is true. Hour solution ranking is false. Individual impact is true.	english	24.18000030517578	43	\N	30	\N	2026-04-01 15:58:54.866591	2026-04-01 15:58:54.8666
48	94	The customer fate is true, trigger event and impact is false, sales target true, decision making process true, decision influencer false, mentor true, trigger priority true, alternatives true, our solution ranking true, individual impact true.	english	20.280000686645508	35	\N	30	\N	2026-04-01 16:30:48.045311	2026-04-01 16:30:48.045321
49	95	The customer fit is true, trigger event and impact false, sales target true, decision making process true, decision influencers true, mentor true, trigger priority true, alternatives true, power solution ranking true, individual impact yes.	english	23.459999084472656	34	\N	30	\N	2026-04-01 18:44:01.597551	2026-04-01 18:44:01.597554
50	96	Here, the customer fit is true, the trigger event and impact is true, sales target false, decision making process, it should be false, decision influencer, my true, mentor, true, trigger priority, true, alternatives, I believe it's false, our solution ranking must be true, individual impact, yes, it's true.	english	26.520000457763672	48	\N	30	\N	2026-04-06 10:00:31.298549	2026-04-06 10:00:31.298552
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, first_name, last_name, role, organization_id, team_id, is_active, last_login, created_at, updated_at, password_hash, is_verified, failed_login_attempts, locked_until, password_reset_token, password_reset_expires, email_verification_token, email_verification_expires, deleted_at, deleted_by, must_change_password, direct_dial, cell_phone, job_title) FROM stdin;
11	admin@millaugroup.com	Sarah	Johnson	ADMIN	5	4	t	2026-06-14 15:17:50.492097	2025-12-05 15:12:49.054996	2026-06-14 15:17:50.510946	$2b$12$84EJjGQZ5V9T3jelod159uHYnEqfP8pcCq5xYHLUR09ywWjEQqPim	t	0	\N	\N	\N	\N	\N	\N	\N	f	(212) 456-7890	(212) 453-5456	\N
47	hafizfarooq78692@gmail.com	Hafiz	Farooq	MANAGER	5	4	t	2026-06-14 16:02:17.270863	2026-06-14 15:25:58.378316	2026-06-14 16:02:17.272623	$2b$12$Rn54PnRHdUiWOH27DYO/E.phoyl.8gd2DUIN6/HK48pGfipwZXklW	t	0	\N	\N	\N	\N	\N	\N	\N	t	(332) 465-3687	\N	VP Sales
14	rep@millaugroup.com	David	Martinez	REP	5	4	t	2026-06-12 12:03:54.586223	2025-12-05 15:12:49.05501	2026-06-12 12:03:54.590141	$2b$12$qbp21dIufHQRlbXYAzTU1OHX3drwxP3bE7zXdJ4DciUUJGkFBFvkW	t	0	\N	\N	\N	\N	\N	\N	\N	f	\N	\N	\N
13	manager@millaugroup.com	Jennifer	Williams	MANAGER	5	4	t	2026-06-12 23:58:31.774872	2025-12-05 15:12:49.055008	2026-06-12 23:58:31.775559	$2b$12$tnAUuNHWAOehkc65uLjy6uzA.KrT7W5M8fGixb2t4lAzPhYV/S.u.	t	0	\N	\N	\N	\N	\N	\N	\N	f	\N	\N	\N
46	davevarner@mac.com	David	Varner	ADMIN	7	\N	t	\N	2026-06-13 17:49:22.315383	2026-06-13 17:49:22.315391	$2b$12$F/3yoByztmGJ9cQkDR8sbO9Z3EDK9b51KW1ghJwJcOpRgqIu64Bde	t	0	\N	\N	\N	\N	\N	\N	\N	t	(212) 456-7890	\N	\N
15	system_admin@millaugroup.com	The Millau	Group Global	SYSTEM_ADMIN	\N	\N	t	2026-06-14 13:57:42.522296	2025-12-11 21:02:15.006348	2026-06-14 13:57:42.552722	$2b$12$0I2ryjdpvPd0hZr6HVWilORxL7EgbBiz9tImgYYJ3le5eBQKqI4ZS	t	0	\N	\N	\N	\N	\N	\N	\N	f	\N	\N	\N
\.


--
-- Name: audio_files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audio_files_id_seq', 58, true);


--
-- Name: checklist_categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.checklist_categories_id_seq', 52, true);


--
-- Name: checklist_item_behaviours_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.checklist_item_behaviours_id_seq', 163, true);


--
-- Name: checklist_item_notes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.checklist_item_notes_id_seq', 66, true);


--
-- Name: checklist_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.checklist_items_id_seq', 143, true);


--
-- Name: coaching_feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.coaching_feedback_id_seq', 50, true);


--
-- Name: coaching_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.coaching_questions_id_seq', 106, true);


--
-- Name: invitations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.invitations_id_seq', 19, true);


--
-- Name: manager_notes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.manager_notes_id_seq', 19, true);


--
-- Name: organization_registration_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.organization_registration_requests_id_seq', 1, true);


--
-- Name: organization_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.organization_settings_id_seq', 3, true);


--
-- Name: organizations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.organizations_id_seq', 7, true);


--
-- Name: reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.reports_id_seq', 41, true);


--
-- Name: score_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.score_history_id_seq', 27, true);


--
-- Name: scoring_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.scoring_results_id_seq', 61, true);


--
-- Name: session_response_analysis_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.session_response_analysis_id_seq', 2269, true);


--
-- Name: session_responses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.session_responses_id_seq', 952, true);


--
-- Name: sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sessions_id_seq', 103, true);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teams_id_seq', 6, true);


--
-- Name: transcripts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.transcripts_id_seq', 50, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 47, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audio_files audio_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audio_files
    ADD CONSTRAINT audio_files_pkey PRIMARY KEY (id);


--
-- Name: audio_files audio_files_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audio_files
    ADD CONSTRAINT audio_files_session_id_key UNIQUE (session_id);


--
-- Name: checklist_categories checklist_categories_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_categories
    ADD CONSTRAINT checklist_categories_name_key UNIQUE (name);


--
-- Name: checklist_categories checklist_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_categories
    ADD CONSTRAINT checklist_categories_pkey PRIMARY KEY (id);


--
-- Name: checklist_item_behaviours checklist_item_behaviours_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_behaviours
    ADD CONSTRAINT checklist_item_behaviours_pkey PRIMARY KEY (id);


--
-- Name: checklist_item_notes checklist_item_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_notes
    ADD CONSTRAINT checklist_item_notes_pkey PRIMARY KEY (id);


--
-- Name: checklist_items checklist_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_items
    ADD CONSTRAINT checklist_items_pkey PRIMARY KEY (id);


--
-- Name: coaching_feedback coaching_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaching_feedback
    ADD CONSTRAINT coaching_feedback_pkey PRIMARY KEY (id);


--
-- Name: coaching_feedback coaching_feedback_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaching_feedback
    ADD CONSTRAINT coaching_feedback_session_id_key UNIQUE (session_id);


--
-- Name: coaching_questions coaching_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaching_questions
    ADD CONSTRAINT coaching_questions_pkey PRIMARY KEY (id);


--
-- Name: invitations invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_pkey PRIMARY KEY (id);


--
-- Name: invitations invitations_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_token_key UNIQUE (token);


--
-- Name: manager_notes manager_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.manager_notes
    ADD CONSTRAINT manager_notes_pkey PRIMARY KEY (id);


--
-- Name: organization_registration_requests organization_registration_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_registration_requests
    ADD CONSTRAINT organization_registration_requests_pkey PRIMARY KEY (id);


--
-- Name: organization_settings organization_settings_organization_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_organization_id_key UNIQUE (organization_id);


--
-- Name: organization_settings organization_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: reports reports_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_session_id_key UNIQUE (session_id);


--
-- Name: score_history score_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_history
    ADD CONSTRAINT score_history_pkey PRIMARY KEY (id);


--
-- Name: scoring_results scoring_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scoring_results
    ADD CONSTRAINT scoring_results_pkey PRIMARY KEY (id);


--
-- Name: scoring_results scoring_results_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scoring_results
    ADD CONSTRAINT scoring_results_session_id_key UNIQUE (session_id);


--
-- Name: session_response_analysis session_response_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_response_analysis
    ADD CONSTRAINT session_response_analysis_pkey PRIMARY KEY (id);


--
-- Name: session_responses session_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_responses
    ADD CONSTRAINT session_responses_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: transcripts transcripts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transcripts
    ADD CONSTRAINT transcripts_pkey PRIMARY KEY (id);


--
-- Name: transcripts transcripts_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transcripts
    ADD CONSTRAINT transcripts_session_id_key UNIQUE (session_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_checklist_items_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_checklist_items_category ON public.checklist_items USING btree (category_id);


--
-- Name: idx_cib_checklist_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cib_checklist_item_id ON public.checklist_item_behaviours USING btree (checklist_item_id);


--
-- Name: idx_invitations_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invitations_email ON public.invitations USING btree (email);


--
-- Name: idx_invitations_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invitations_organization_id ON public.invitations USING btree (organization_id);


--
-- Name: idx_invitations_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invitations_token ON public.invitations USING btree (token);


--
-- Name: idx_manager_notes_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_manager_notes_created_at ON public.manager_notes USING btree (created_at DESC);


--
-- Name: idx_organization_settings_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organization_settings_organization_id ON public.organization_settings USING btree (organization_id);


--
-- Name: idx_responses_item_answer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_responses_item_answer ON public.session_responses USING btree (item_id, ai_answer);


--
-- Name: idx_responses_session_answer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_responses_session_answer ON public.session_responses USING btree (session_id, ai_answer);


--
-- Name: idx_responses_session_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_responses_session_item ON public.session_responses USING btree (session_id, item_id);


--
-- Name: idx_score_history_session_calc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_score_history_session_calc ON public.score_history USING btree (session_id, calculated_at DESC);


--
-- Name: idx_score_history_version; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_score_history_version ON public.score_history USING btree (session_id, version_number);


--
-- Name: idx_scoring_risk_band; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scoring_risk_band ON public.scoring_results USING btree (risk_band);


--
-- Name: idx_scoring_score_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scoring_score_desc ON public.scoring_results USING btree (total_score DESC);


--
-- Name: idx_scoring_session_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scoring_session_score ON public.scoring_results USING btree (session_id, total_score);


--
-- Name: idx_scoring_total_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scoring_total_score ON public.scoring_results USING btree (total_score);


--
-- Name: idx_sessions_deal_stage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_deal_stage ON public.sessions USING btree (deal_stage);


--
-- Name: idx_sessions_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_mode ON public.sessions USING btree (session_mode);


--
-- Name: idx_sessions_status_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_status_updated ON public.sessions USING btree (status, updated_at);


--
-- Name: idx_sessions_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_user_status ON public.sessions USING btree (user_id, status);


--
-- Name: idx_sessions_user_updated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_user_updated ON public.sessions USING btree (user_id, updated_at);


--
-- Name: idx_sessions_user_updated_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_user_updated_desc ON public.sessions USING btree (user_id, updated_at DESC);


--
-- Name: idx_users_org_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_org_active ON public.users USING btree (organization_id, is_active);


--
-- Name: idx_users_team_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_team_active ON public.users USING btree (team_id, is_active);


--
-- Name: idx_users_team_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_team_role ON public.users USING btree (team_id, role);


--
-- Name: ix_audio_files_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audio_files_id ON public.audio_files USING btree (id);


--
-- Name: ix_checklist_categories_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_categories_id ON public.checklist_categories USING btree (id);


--
-- Name: ix_checklist_item_behaviours_checklistitemname; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_behaviours_checklistitemname ON public.checklist_item_behaviours USING btree (checklistitemname);


--
-- Name: ix_checklist_item_behaviours_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_behaviours_id ON public.checklist_item_behaviours USING btree (id);


--
-- Name: ix_checklist_item_behaviours_isactive; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_behaviours_isactive ON public.checklist_item_behaviours USING btree (isactive);


--
-- Name: ix_checklist_item_behaviours_rowtype; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_behaviours_rowtype ON public.checklist_item_behaviours USING btree (rowtype);


--
-- Name: ix_checklist_item_notes_checklist_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_checklist_item_id ON public.checklist_item_notes USING btree (checklist_item_id);


--
-- Name: ix_checklist_item_notes_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_created_by_user_id ON public.checklist_item_notes USING btree (created_by_user_id);


--
-- Name: ix_checklist_item_notes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_id ON public.checklist_item_notes USING btree (id);


--
-- Name: ix_checklist_item_notes_opp_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_opp_item ON public.checklist_item_notes USING btree (opportunity_key, checklist_item_id);


--
-- Name: ix_checklist_item_notes_opportunity_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_opportunity_key ON public.checklist_item_notes USING btree (opportunity_key);


--
-- Name: ix_checklist_item_notes_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_session_id ON public.checklist_item_notes USING btree (session_id);


--
-- Name: ix_checklist_item_notes_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_updated_at ON public.checklist_item_notes USING btree (updated_at);


--
-- Name: ix_checklist_item_notes_version_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_item_notes_version_lookup ON public.checklist_item_notes USING btree (checklist_item_id, opportunity_key, version);


--
-- Name: ix_checklist_items_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checklist_items_id ON public.checklist_items USING btree (id);


--
-- Name: ix_coaching_feedback_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coaching_feedback_id ON public.coaching_feedback USING btree (id);


--
-- Name: ix_coaching_questions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_coaching_questions_id ON public.coaching_questions USING btree (id);


--
-- Name: ix_manager_notes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_manager_notes_id ON public.manager_notes USING btree (id);


--
-- Name: ix_manager_notes_manager_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_manager_notes_manager_id ON public.manager_notes USING btree (manager_id);


--
-- Name: ix_manager_notes_note_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_manager_notes_note_type ON public.manager_notes USING btree (note_type);


--
-- Name: ix_manager_notes_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_manager_notes_session_id ON public.manager_notes USING btree (session_id);


--
-- Name: ix_organization_registration_requests_admin_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_registration_requests_admin_email ON public.organization_registration_requests USING btree (admin_email);


--
-- Name: ix_organization_registration_requests_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_registration_requests_id ON public.organization_registration_requests USING btree (id);


--
-- Name: ix_organization_registration_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organization_registration_requests_status ON public.organization_registration_requests USING btree (status);


--
-- Name: ix_organizations_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_id ON public.organizations USING btree (id);


--
-- Name: ix_reports_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reports_id ON public.reports USING btree (id);


--
-- Name: ix_score_history_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_score_history_id ON public.score_history USING btree (id);


--
-- Name: ix_score_history_scoring_result_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_score_history_scoring_result_id ON public.score_history USING btree (scoring_result_id);


--
-- Name: ix_score_history_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_score_history_session_id ON public.score_history USING btree (session_id);


--
-- Name: ix_scoring_results_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scoring_results_id ON public.scoring_results USING btree (id);


--
-- Name: ix_session_response_analysis_behaviour_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_response_analysis_behaviour_id ON public.session_response_analysis USING btree (behaviour_id);


--
-- Name: ix_session_response_analysis_evidence_found; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_response_analysis_evidence_found ON public.session_response_analysis USING btree (evidence_found);


--
-- Name: ix_session_response_analysis_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_response_analysis_id ON public.session_response_analysis USING btree (id);


--
-- Name: ix_session_response_analysis_session_response_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_response_analysis_session_response_id ON public.session_response_analysis USING btree (session_response_id);


--
-- Name: ix_session_responses_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_responses_id ON public.session_responses USING btree (id);


--
-- Name: ix_sessions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sessions_id ON public.sessions USING btree (id);


--
-- Name: ix_teams_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teams_id ON public.teams USING btree (id);


--
-- Name: ix_transcripts_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_transcripts_id ON public.transcripts USING btree (id);


--
-- Name: ix_users_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_deleted_at ON public.users USING btree (deleted_at);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: uq_checklist_item_notes_active_per_item_opportunity; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_checklist_item_notes_active_per_item_opportunity ON public.checklist_item_notes USING btree (checklist_item_id, opportunity_key) WHERE (is_active = true);


--
-- Name: audio_files audio_files_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audio_files
    ADD CONSTRAINT audio_files_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: checklist_item_notes checklist_item_notes_checklist_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_notes
    ADD CONSTRAINT checklist_item_notes_checklist_item_id_fkey FOREIGN KEY (checklist_item_id) REFERENCES public.checklist_items(id) ON DELETE CASCADE;


--
-- Name: checklist_item_notes checklist_item_notes_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_notes
    ADD CONSTRAINT checklist_item_notes_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: checklist_item_notes checklist_item_notes_previous_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_notes
    ADD CONSTRAINT checklist_item_notes_previous_version_id_fkey FOREIGN KEY (previous_version_id) REFERENCES public.checklist_item_notes(id) ON DELETE SET NULL;


--
-- Name: checklist_item_notes checklist_item_notes_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_notes
    ADD CONSTRAINT checklist_item_notes_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE SET NULL;


--
-- Name: checklist_item_notes checklist_item_notes_updated_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_notes
    ADD CONSTRAINT checklist_item_notes_updated_by_user_id_fkey FOREIGN KEY (updated_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: checklist_items checklist_items_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_items
    ADD CONSTRAINT checklist_items_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.checklist_categories(id) ON DELETE CASCADE;


--
-- Name: coaching_feedback coaching_feedback_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaching_feedback
    ADD CONSTRAINT coaching_feedback_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: coaching_questions coaching_questions_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaching_questions
    ADD CONSTRAINT coaching_questions_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.checklist_items(id) ON DELETE CASCADE;


--
-- Name: checklist_item_behaviours fk_checklist_item_behaviours_item_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.checklist_item_behaviours
    ADD CONSTRAINT fk_checklist_item_behaviours_item_id FOREIGN KEY (checklist_item_id) REFERENCES public.checklist_items(id) ON DELETE CASCADE;


--
-- Name: users fk_users_deleted_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_deleted_by FOREIGN KEY (deleted_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invitations invitations_invited_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_invited_by_fkey FOREIGN KEY (invited_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: invitations invitations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: invitations invitations_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: manager_notes manager_notes_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.manager_notes
    ADD CONSTRAINT manager_notes_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: manager_notes manager_notes_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.manager_notes
    ADD CONSTRAINT manager_notes_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: organization_registration_requests organization_registration_requests_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_registration_requests
    ADD CONSTRAINT organization_registration_requests_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: organization_registration_requests organization_registration_requests_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_registration_requests
    ADD CONSTRAINT organization_registration_requests_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: organization_settings organization_settings_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: reports reports_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: score_history score_history_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_history
    ADD CONSTRAINT score_history_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: score_history score_history_scoring_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_history
    ADD CONSTRAINT score_history_scoring_result_id_fkey FOREIGN KEY (scoring_result_id) REFERENCES public.scoring_results(id) ON DELETE SET NULL;


--
-- Name: score_history score_history_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.score_history
    ADD CONSTRAINT score_history_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: scoring_results scoring_results_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scoring_results
    ADD CONSTRAINT scoring_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: session_response_analysis session_response_analysis_behaviour_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_response_analysis
    ADD CONSTRAINT session_response_analysis_behaviour_id_fkey FOREIGN KEY (behaviour_id) REFERENCES public.checklist_item_behaviours(id) ON DELETE CASCADE;


--
-- Name: session_response_analysis session_response_analysis_session_response_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_response_analysis
    ADD CONSTRAINT session_response_analysis_session_response_id_fkey FOREIGN KEY (session_response_id) REFERENCES public.session_responses(id) ON DELETE CASCADE;


--
-- Name: session_responses session_responses_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_responses
    ADD CONSTRAINT session_responses_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.checklist_items(id) ON DELETE CASCADE;


--
-- Name: session_responses session_responses_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_responses
    ADD CONSTRAINT session_responses_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: teams teams_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: transcripts transcripts_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transcripts
    ADD CONSTRAINT transcripts_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: users users_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: users users_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict XPmRcUiIWSZ0eKaoscgxGuRvBemsN8HcoV0QAglhQHiO9sFVbzQ4RP2sY2pQQTt

