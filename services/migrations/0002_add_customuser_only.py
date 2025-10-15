from django.db import migrations

CREATE_CUSTOMUSER = """
CREATE TABLE IF NOT EXISTS services_customuser (
    id BIGSERIAL PRIMARY KEY,
    last_login TIMESTAMPTZ NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE
);
"""

# M2M: пользователь ↔ группы
CREATE_CUSTOMUSER_GROUPS = """
CREATE TABLE IF NOT EXISTS services_customuser_groups (
    id BIGSERIAL PRIMARY KEY,
    customuser_id BIGINT NOT NULL,
    group_id INTEGER NOT NULL,
    UNIQUE (customuser_id, group_id),
    CONSTRAINT services_customuser_groups_customuser_fk
        FOREIGN KEY (customuser_id) REFERENCES services_customuser(id)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT services_customuser_groups_group_fk
        FOREIGN KEY (group_id) REFERENCES auth_group(id)
        DEFERRABLE INITIALLY DEFERRED
);
"""

# M2M: пользователь ↔ права
CREATE_CUSTOMUSER_PERMS = """
CREATE TABLE IF NOT EXISTS services_customuser_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    customuser_id BIGINT NOT NULL,
    permission_id INTEGER NOT NULL,
    UNIQUE (customuser_id, permission_id),
    CONSTRAINT services_customuser_perms_customuser_fk
        FOREIGN KEY (customuser_id) REFERENCES services_customuser(id)
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT services_customuser_perms_permission_fk
        FOREIGN KEY (permission_id) REFERENCES auth_permission(id)
        DEFERRABLE INITIALLY DEFERRED
);
"""

DROP_CUSTOMUSER_PERMS = "DROP TABLE IF EXISTS services_customuser_user_permissions;"
DROP_CUSTOMUSER_GROUPS = "DROP TABLE IF EXISTS services_customuser_groups;"
DROP_CUSTOMUSER = "DROP TABLE IF EXISTS services_customuser;"

class Migration(migrations.Migration):
    dependencies = [
        ("services", "0001_initial"),     # 0001 мы отметили --fake
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunSQL(CREATE_CUSTOMUSER, DROP_CUSTOMUSER),
        migrations.RunSQL(CREATE_CUSTOMUSER_GROUPS, DROP_CUSTOMUSER_GROUPS),
        migrations.RunSQL(CREATE_CUSTOMUSER_PERMS, DROP_CUSTOMUSER_PERMS),
    ]