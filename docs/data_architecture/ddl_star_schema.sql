-- =============================================================================
-- DDL: Data Mart Clientes y Ventas - Esquema Dimensional en Estrella
-- Arquitectura: Kimball Star Schema con SCD Tipo 2
-- Base de Datos Compatible: PostgreSQL / Snowflake / Databricks / DuckDB / Synapse
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. DIMENSIÓN FECHA
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mart_sales.dim_date (
    date_sk INT PRIMARY KEY,
    full_date DATE NOT NULL,
    day_of_month INT NOT NULL,
    month_number INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter_number INT NOT NULL,
    year_number INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE
);

-- -----------------------------------------------------------------------------
-- 2. DIMENSIÓN CLIENTE (SCD TIPO 2)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mart_sales.dim_customer (
    customer_sk BIGINT PRIMARY KEY,
    customer_id VARCHAR(30) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_class_id VARCHAR(30) NOT NULL,
    customer_class_desc VARCHAR(100),
    corporate_customer_id VARCHAR(30),
    primary_contact VARCHAR(100),
    address_line1 VARCHAR(150),
    city VARCHAR(50),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50),
    phone_number VARCHAR(50),
    salesperson_id VARCHAR(30),
    territory_id VARCHAR(30),
    payment_terms_id VARCHAR(30),
    credit_limit_amount NUMERIC(19, 2),
    credit_limit_type SMALLINT,
    is_inactive_source TINYINT NOT NULL DEFAULT 0,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59',
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    row_hash VARCHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dim_customer_id ON mart_sales.dim_customer(customer_id);
CREATE INDEX IF NOT EXISTS idx_dim_customer_active ON mart_sales.dim_customer(customer_id, is_current);

-- -----------------------------------------------------------------------------
-- 3. DIMENSIÓN PRODUCTO
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mart_sales.dim_product (
    product_sk BIGINT PRIMARY KEY,
    item_number VARCHAR(50) NOT NULL,
    item_description VARCHAR(150) NOT NULL,
    item_class_code VARCHAR(30),
    item_generic_desc VARCHAR(100),
    standard_cost NUMERIC(19, 4),
    current_cost NUMERIC(19, 4),
    uom_schedule VARCHAR(30),
    decimal_places_qty SMALLINT,
    decimal_places_curr SMALLINT,
    is_active TINYINT NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_dim_product_item_number ON mart_sales.dim_product(item_number);

-- -----------------------------------------------------------------------------
-- 4. DIMENSIONES VENDEDOR Y TERRITORIO
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mart_sales.dim_salesperson (
    salesperson_sk BIGINT PRIMARY KEY,
    salesperson_id VARCHAR(30) NOT NULL,
    employee_id VARCHAR(30),
    full_name VARCHAR(100) NOT NULL,
    job_title VARCHAR(50),
    territory_id VARCHAR(30),
    commission_percent SMALLINT,
    is_inactive TINYINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mart_sales.dim_territory (
    territory_sk BIGINT PRIMARY KEY,
    territory_id VARCHAR(30) NOT NULL,
    territory_description VARCHAR(100),
    manager_full_name VARCHAR(100),
    country VARCHAR(50),
    is_inactive TINYINT NOT NULL DEFAULT 0
);

-- -----------------------------------------------------------------------------
-- 5. TABLA DE HECHOS: VENTAS TRANSACCIONALES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mart_sales.fact_sales (
    sales_fact_sk BIGINT PRIMARY KEY,
    invoice_number VARCHAR(30) NOT NULL,
    line_item_sequence INT NOT NULL,
    component_sequence INT NOT NULL DEFAULT 0,
    document_date_sk INT NOT NULL REFERENCES mart_sales.dim_date(date_sk),
    gl_post_date_sk INT NOT NULL REFERENCES mart_sales.dim_date(date_sk),
    customer_sk BIGINT NOT NULL REFERENCES mart_sales.dim_customer(customer_sk),
    product_sk BIGINT NOT NULL REFERENCES mart_sales.dim_product(product_sk),
    salesperson_sk BIGINT NOT NULL REFERENCES mart_sales.dim_salesperson(salesperson_sk),
    territory_sk BIGINT NOT NULL REFERENCES mart_sales.dim_territory(territory_sk),
    sop_type SMALLINT NOT NULL,
    doc_type_desc VARCHAR(30) NOT NULL,
    doc_id VARCHAR(30),
    currency_id VARCHAR(20),
    uofm VARCHAR(20),
    location_code VARCHAR(30),
    quantity NUMERIC(19, 4) NOT NULL,
    unit_price NUMERIC(19, 4) NOT NULL,
    extended_price NUMERIC(19, 2) NOT NULL,
    unit_cost NUMERIC(19, 4) NOT NULL,
    extended_cost NUMERIC(19, 2) NOT NULL,
    markdown_amount NUMERIC(19, 2) NOT NULL DEFAULT 0,
    net_sales_amount NUMERIC(19, 2) NOT NULL,
    gross_profit_amount NUMERIC(19, 2) NOT NULL,
    gross_profit_margin_pct NUMERIC(8, 4),
    is_voided TINYINT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_docdate ON mart_sales.fact_sales(document_date_sk);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON mart_sales.fact_sales(customer_sk);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON mart_sales.fact_sales(product_sk);

-- -----------------------------------------------------------------------------
-- 6. TABLA DE HECHOS: SNAPSHOT MENSUAL DE CLIENTES (CHURN & LTV)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mart_sales.fact_customer_monthly_snapshot (
    snapshot_sk BIGINT PRIMARY KEY,
    year_month_sk INT NOT NULL REFERENCES mart_sales.dim_date(date_sk),
    customer_sk BIGINT NOT NULL REFERENCES mart_sales.dim_customer(customer_sk),
    salesperson_sk BIGINT NOT NULL REFERENCES mart_sales.dim_salesperson(salesperson_sk),
    territory_sk BIGINT NOT NULL REFERENCES mart_sales.dim_territory(territory_sk),
    customer_id VARCHAR(30) NOT NULL,
    active_month_flag INT NOT NULL DEFAULT 0,
    is_churned_flag INT NOT NULL DEFAULT 0,
    is_new_customer_flag INT NOT NULL DEFAULT 0,
    is_reactivated_flag INT NOT NULL DEFAULT 0,
    total_invoices_month INT NOT NULL DEFAULT 0,
    total_returns_month INT NOT NULL DEFAULT 0,
    gross_sales_month NUMERIC(19, 2) NOT NULL DEFAULT 0,
    returns_amount_month NUMERIC(19, 2) NOT NULL DEFAULT 0,
    net_sales_month NUMERIC(19, 2) NOT NULL DEFAULT 0,
    total_cogs_month NUMERIC(19, 2) NOT NULL DEFAULT 0,
    gross_profit_month NUMERIC(19, 2) NOT NULL DEFAULT 0,
    cumulative_net_sales_ltv NUMERIC(19, 2) NOT NULL DEFAULT 0,
    cumulative_gross_profit_ltv NUMERIC(19, 2) NOT NULL DEFAULT 0,
    days_since_last_purchase INT,
    last_purchase_date DATE
);

CREATE INDEX IF NOT EXISTS idx_cust_snap_month ON mart_sales.fact_customer_monthly_snapshot(year_month_sk);
CREATE INDEX IF NOT EXISTS idx_cust_snap_cust ON mart_sales.fact_customer_monthly_snapshot(customer_id);
