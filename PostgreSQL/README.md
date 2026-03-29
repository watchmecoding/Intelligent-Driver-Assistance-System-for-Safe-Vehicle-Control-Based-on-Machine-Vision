psql -U postgres -d driver_monitoring -f sql/01_create_tables.sql
psql -U postgres -d driver_monitoring -f sql/02_seed_data.sql