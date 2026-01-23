// =============================================================================
// AEGIS Graph Schema Definition
// Gremlin schema for JanusGraph / Neptune
// =============================================================================

// This script defines the graph schema for the AEGIS Healthcare Knowledge Graph
// Run this against JanusGraph or use as reference for Neptune

// =============================================================================
// VERTEX LABELS (Entity Types)
// =============================================================================

// Core Domain
mgmt = graph.openManagement()

// Patient
patient = mgmt.makeVertexLabel('Patient').make()

// Provider
provider = mgmt.makeVertexLabel('Provider').make()

// Organization
organization = mgmt.makeVertexLabel('Organization').make()

// Payer (subtype of Organization)
payer = mgmt.makeVertexLabel('Payer').make()

// Location
location = mgmt.makeVertexLabel('Location').make()

// Clinical Domain
encounter = mgmt.makeVertexLabel('Encounter').make()
diagnosis = mgmt.makeVertexLabel('Diagnosis').make()
procedure = mgmt.makeVertexLabel('Procedure').make()
observation = mgmt.makeVertexLabel('Observation').make()
medication = mgmt.makeVertexLabel('Medication').make()
allergyIntolerance = mgmt.makeVertexLabel('AllergyIntolerance').make()
clinicalNote = mgmt.makeVertexLabel('ClinicalNote').make()

// Financial Domain
coverage = mgmt.makeVertexLabel('Coverage').make()
claim = mgmt.makeVertexLabel('Claim').make()
claimLine = mgmt.makeVertexLabel('ClaimLine').make()
denial = mgmt.makeVertexLabel('Denial').make()
appeal = mgmt.makeVertexLabel('Appeal').make()
payment = mgmt.makeVertexLabel('Payment').make()
authorization = mgmt.makeVertexLabel('Authorization').make()

mgmt.commit()

// =============================================================================
// EDGE LABELS (Relationships)
// =============================================================================

mgmt = graph.openManagement()

// Core Relationships
hasEncounter = mgmt.makeEdgeLabel('HAS_ENCOUNTER').multiplicity(ONE2MANY).make()
belongsToOrganization = mgmt.makeEdgeLabel('BELONGS_TO_ORGANIZATION').multiplicity(MANY2ONE).make()
hasPrimaryProvider = mgmt.makeEdgeLabel('HAS_PRIMARY_PROVIDER').multiplicity(MANY2ONE).make()
locatedAt = mgmt.makeEdgeLabel('LOCATED_AT').multiplicity(MANY2ONE).make()
partOf = mgmt.makeEdgeLabel('PART_OF').multiplicity(MANY2ONE).make()

// Clinical Relationships
hasDiagnosis = mgmt.makeEdgeLabel('HAS_DIAGNOSIS').multiplicity(ONE2MANY).make()
hasProcedure = mgmt.makeEdgeLabel('HAS_PROCEDURE').multiplicity(ONE2MANY).make()
hasObservation = mgmt.makeEdgeLabel('HAS_OBSERVATION').multiplicity(ONE2MANY).make()
hasMedication = mgmt.makeEdgeLabel('HAS_MEDICATION').multiplicity(ONE2MANY).make()
hasAllergy = mgmt.makeEdgeLabel('HAS_ALLERGY').multiplicity(ONE2MANY).make()
attendedBy = mgmt.makeEdgeLabel('ATTENDED_BY').multiplicity(MANY2ONE).make()
performedBy = mgmt.makeEdgeLabel('PERFORMED_BY').multiplicity(MANY2ONE).make()
locatedIn = mgmt.makeEdgeLabel('LOCATED_IN').multiplicity(MANY2ONE).make()
justifiedBy = mgmt.makeEdgeLabel('JUSTIFIED_BY').multiplicity(MANY2MANY).make()
resultsIn = mgmt.makeEdgeLabel('RESULTS_IN').multiplicity(ONE2MANY).make()

// Financial Relationships
hasCoverage = mgmt.makeEdgeLabel('HAS_COVERAGE').multiplicity(ONE2MANY).make()
providedBy = mgmt.makeEdgeLabel('PROVIDED_BY').multiplicity(MANY2ONE).make()
billedFor = mgmt.makeEdgeLabel('BILLED_FOR').multiplicity(ONE2MANY).make()
submittedTo = mgmt.makeEdgeLabel('SUBMITTED_TO').multiplicity(MANY2ONE).make()
hasDenial = mgmt.makeEdgeLabel('HAS_DENIAL').multiplicity(ONE2MANY).make()
hasPayment = mgmt.makeEdgeLabel('HAS_PAYMENT').multiplicity(ONE2MANY).make()
appealedWith = mgmt.makeEdgeLabel('APPEALED_WITH').multiplicity(ONE2MANY).make()
hasClaimLine = mgmt.makeEdgeLabel('HAS_CLAIM_LINE').multiplicity(ONE2MANY).make()
requiresAuthorization = mgmt.makeEdgeLabel('REQUIRES_AUTHORIZATION').multiplicity(MANY2ONE).make()
supportedBy = mgmt.makeEdgeLabel('SUPPORTED_BY').multiplicity(MANY2MANY).make()

// Temporal Relationships
precededBy = mgmt.makeEdgeLabel('PRECEDED_BY').multiplicity(MANY2ONE).make()
followedBy = mgmt.makeEdgeLabel('FOLLOWED_BY').multiplicity(MANY2ONE).make()
causedBy = mgmt.makeEdgeLabel('CAUSED_BY').multiplicity(MANY2MANY).make()
resultedIn = mgmt.makeEdgeLabel('RESULTED_IN').multiplicity(MANY2MANY).make()

// Similarity/Pattern Relationships
similarTo = mgmt.makeEdgeLabel('SIMILAR_TO').multiplicity(MANY2MANY).make()

mgmt.commit()

// =============================================================================
// PROPERTY KEYS
// =============================================================================

mgmt = graph.openManagement()

// Common Properties (all vertices)
tenantId = mgmt.makePropertyKey('tenant_id').dataType(String.class).make()
sourceSystem = mgmt.makePropertyKey('source_system').dataType(String.class).make()
sourceId = mgmt.makePropertyKey('source_id').dataType(String.class).make()
createdAt = mgmt.makePropertyKey('created_at').dataType(Date.class).make()
updatedAt = mgmt.makePropertyKey('updated_at').dataType(Date.class).make()

// Patient Properties
mrn = mgmt.makePropertyKey('mrn').dataType(String.class).make()
givenName = mgmt.makePropertyKey('given_name').dataType(String.class).make()
familyName = mgmt.makePropertyKey('family_name').dataType(String.class).make()
birthDate = mgmt.makePropertyKey('birth_date').dataType(Date.class).make()
gender = mgmt.makePropertyKey('gender').dataType(String.class).make()
ssn = mgmt.makePropertyKey('ssn').dataType(String.class).make()
phoneNumber = mgmt.makePropertyKey('phone_number').dataType(String.class).make()
email = mgmt.makePropertyKey('email').dataType(String.class).make()
addressLine = mgmt.makePropertyKey('address_line').dataType(String.class).make()
city = mgmt.makePropertyKey('city').dataType(String.class).make()
state = mgmt.makePropertyKey('state').dataType(String.class).make()
postalCode = mgmt.makePropertyKey('postal_code').dataType(String.class).make()

// Provider Properties
npi = mgmt.makePropertyKey('npi').dataType(String.class).make()
specialty = mgmt.makePropertyKey('specialty').dataType(String.class).make()
credentials = mgmt.makePropertyKey('credentials').dataType(String.class).make()

// Organization Properties
organizationName = mgmt.makePropertyKey('organization_name').dataType(String.class).make()
organizationType = mgmt.makePropertyKey('organization_type').dataType(String.class).make()
taxId = mgmt.makePropertyKey('tax_id').dataType(String.class).make()

// Location Properties
locationName = mgmt.makePropertyKey('location_name').dataType(String.class).make()
locationType = mgmt.makePropertyKey('location_type').dataType(String.class).make()
bedStatus = mgmt.makePropertyKey('bed_status').dataType(String.class).make()

// Encounter Properties
encounterType = mgmt.makePropertyKey('encounter_type').dataType(String.class).make()
encounterClass = mgmt.makePropertyKey('encounter_class').dataType(String.class).make()
encounterStatus = mgmt.makePropertyKey('encounter_status').dataType(String.class).make()
admitDate = mgmt.makePropertyKey('admit_date').dataType(Date.class).make()
dischargeDate = mgmt.makePropertyKey('discharge_date').dataType(Date.class).make()
admitSource = mgmt.makePropertyKey('admit_source').dataType(String.class).make()
dischargeDisposition = mgmt.makePropertyKey('discharge_disposition').dataType(String.class).make()
lengthOfStay = mgmt.makePropertyKey('length_of_stay').dataType(Integer.class).make()

// Diagnosis Properties
icd10Code = mgmt.makePropertyKey('icd10_code').dataType(String.class).make()
diagnosisDescription = mgmt.makePropertyKey('diagnosis_description').dataType(String.class).make()
diagnosisType = mgmt.makePropertyKey('diagnosis_type').dataType(String.class).make()
diagnosisRank = mgmt.makePropertyKey('diagnosis_rank').dataType(Integer.class).make()
presentOnAdmission = mgmt.makePropertyKey('present_on_admission').dataType(String.class).make()
onsetDate = mgmt.makePropertyKey('onset_date').dataType(Date.class).make()

// Procedure Properties
cptCode = mgmt.makePropertyKey('cpt_code').dataType(String.class).make()
hcpcsCode = mgmt.makePropertyKey('hcpcs_code').dataType(String.class).make()
procedureDescription = mgmt.makePropertyKey('procedure_description').dataType(String.class).make()
procedureDate = mgmt.makePropertyKey('procedure_date').dataType(Date.class).make()
procedureStatus = mgmt.makePropertyKey('procedure_status').dataType(String.class).make()

// Observation Properties
loincCode = mgmt.makePropertyKey('loinc_code').dataType(String.class).make()
observationType = mgmt.makePropertyKey('observation_type').dataType(String.class).make()
observationValue = mgmt.makePropertyKey('observation_value').dataType(String.class).make()
observationUnit = mgmt.makePropertyKey('observation_unit').dataType(String.class).make()
observationDate = mgmt.makePropertyKey('observation_date').dataType(Date.class).make()
referenceRange = mgmt.makePropertyKey('reference_range').dataType(String.class).make()
interpretation = mgmt.makePropertyKey('interpretation').dataType(String.class).make()

// Claim Properties
claimNumber = mgmt.makePropertyKey('claim_number').dataType(String.class).make()
claimType = mgmt.makePropertyKey('claim_type').dataType(String.class).make()
claimStatus = mgmt.makePropertyKey('claim_status').dataType(String.class).make()
serviceDateStart = mgmt.makePropertyKey('service_date_start').dataType(Date.class).make()
serviceDateEnd = mgmt.makePropertyKey('service_date_end').dataType(Date.class).make()
submissionDate = mgmt.makePropertyKey('submission_date').dataType(Date.class).make()
billedAmount = mgmt.makePropertyKey('billed_amount').dataType(Double.class).make()
allowedAmount = mgmt.makePropertyKey('allowed_amount').dataType(Double.class).make()
paidAmount = mgmt.makePropertyKey('paid_amount').dataType(Double.class).make()
patientResponsibility = mgmt.makePropertyKey('patient_responsibility').dataType(Double.class).make()

// Denial Properties
denialReasonCode = mgmt.makePropertyKey('denial_reason_code').dataType(String.class).make()
denialCategory = mgmt.makePropertyKey('denial_category').dataType(String.class).make()
denialDescription = mgmt.makePropertyKey('denial_description').dataType(String.class).make()
deniedAmount = mgmt.makePropertyKey('denied_amount').dataType(Double.class).make()
denialDate = mgmt.makePropertyKey('denial_date').dataType(Date.class).make()
appealDeadline = mgmt.makePropertyKey('appeal_deadline').dataType(Date.class).make()

// Appeal Properties
appealNumber = mgmt.makePropertyKey('appeal_number').dataType(String.class).make()
appealLevel = mgmt.makePropertyKey('appeal_level').dataType(String.class).make()
appealStatus = mgmt.makePropertyKey('appeal_status').dataType(String.class).make()
appealSubmissionDate = mgmt.makePropertyKey('appeal_submission_date').dataType(Date.class).make()
appealResolutionDate = mgmt.makePropertyKey('appeal_resolution_date').dataType(Date.class).make()
appealOutcome = mgmt.makePropertyKey('appeal_outcome').dataType(String.class).make()
recoveredAmount = mgmt.makePropertyKey('recovered_amount').dataType(Double.class).make()

mgmt.commit()

// =============================================================================
// INDEXES
// =============================================================================

mgmt = graph.openManagement()

// Composite Indexes (exact match queries)

// Patient indexes
mgmt.buildIndex('byMrn', Vertex.class).addKey(mrn).addKey(tenantId).buildCompositeIndex()
mgmt.buildIndex('byPatientName', Vertex.class).addKey(familyName).addKey(givenName).addKey(tenantId).buildCompositeIndex()

// Provider indexes
mgmt.buildIndex('byNpi', Vertex.class).addKey(npi).addKey(tenantId).buildCompositeIndex()

// Encounter indexes
mgmt.buildIndex('byEncounterStatus', Vertex.class).addKey(encounterStatus).addKey(tenantId).buildCompositeIndex()
mgmt.buildIndex('byAdmitDate', Vertex.class).addKey(admitDate).addKey(tenantId).buildCompositeIndex()

// Diagnosis indexes
mgmt.buildIndex('byIcd10', Vertex.class).addKey(icd10Code).addKey(tenantId).buildCompositeIndex()

// Procedure indexes
mgmt.buildIndex('byCpt', Vertex.class).addKey(cptCode).addKey(tenantId).buildCompositeIndex()

// Claim indexes
mgmt.buildIndex('byClaimNumber', Vertex.class).addKey(claimNumber).addKey(tenantId).buildCompositeIndex()
mgmt.buildIndex('byClaimStatus', Vertex.class).addKey(claimStatus).addKey(tenantId).buildCompositeIndex()

// Denial indexes
mgmt.buildIndex('byDenialCategory', Vertex.class).addKey(denialCategory).addKey(tenantId).buildCompositeIndex()
mgmt.buildIndex('byDenialReasonCode', Vertex.class).addKey(denialReasonCode).addKey(tenantId).buildCompositeIndex()

// Appeal indexes
mgmt.buildIndex('byAppealStatus', Vertex.class).addKey(appealStatus).addKey(tenantId).buildCompositeIndex()

// Source system indexes (for deduplication)
mgmt.buildIndex('bySource', Vertex.class).addKey(sourceSystem).addKey(sourceId).addKey(tenantId).buildCompositeIndex()

// Tenant-only index
mgmt.buildIndex('byTenant', Vertex.class).addKey(tenantId).buildCompositeIndex()

mgmt.commit()

// Wait for indexes to be ready
mgmt = graph.openManagement()
mgmt.awaitGraphIndexStatus(graph, 'byMrn').call()
mgmt.awaitGraphIndexStatus(graph, 'byClaimNumber').call()
mgmt.commit()

println "AEGIS Graph Schema created successfully!"
