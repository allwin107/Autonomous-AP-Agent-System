# Entity-Relationship Diagram (ERD)

This diagram visualizes the relationships between the MongoDB collections used in the AI Accounts Payable Employee system.

```mermaid
erDiagram
    INVOICE ||--o{ AUDIT_LOG : "has history"
    INVOICE }|--|| VENDOR : "belongs to"
    INVOICE }|--o| PURCHASE_ORDER : "references"
    INVOICE ||--o{ APPROVAL_REQUEST : "requires"
    INVOICE }|--|| COMPANY_CONFIG : "uses config"
    PURCHASE_ORDER ||--|| GOODS_RECEIPT_NOTE : "matched with"

    INVOICE {
        string invoice_id PK
        string company_id FK
        string vendor_id FK
        string po_reference FK
        string status
        float total
        datetime due_date
    }

    VENDOR {
        string id PK
        string name
        string email
        json bank_details
        string approval_status
        json risk_profile
    }

    PURCHASE_ORDER {
        string po_number PK
        string company_id FK
        string vendor_id FK
        float total_amount
        string status
    }

    GOODS_RECEIPT_NOTE {
        string grn_id PK
        string po_reference FK
        string vendor_id FK
        json items
    }

    AUDIT_LOG {
        string event_id PK
        string invoice_id FK
        string action_type
        datetime timestamp
        string details
    }

    COMPANY_CONFIG {
        string company_id PK
        json matching_tolerance
        json approval_limits
        json gl_mappings
    }

    APPROVAL_REQUEST {
        string request_id PK
        string invoice_id FK
        string assigned_to
        string status
        datetime response_time
    }

    MEMORY_STORE {
        string memory_id PK
        vector content_vector
        json meta_data
        datetime created_at
    }
```

### Key:
- **PK**: Primary Key (Unique Identifier, Indexed)
- **FK**: Foreign Key (Reference to another entity)
- **||--o{**: One-to-Many
- **}|--||**: Many-to-One
- **||--||**: One-to-One
