$(document).ready(function () {

    // Initialize devices table
    var devices_table = $('#devices').DataTable({
        ajax: "/get_devices",
        columns: [            
            { data: 'name', title:'Nombre' },
            { data: 'ae_title', title: 'AE Title' },
            { data: 'address', title: 'Dirección' }
        ],
        searching: false,
        paging: false,
        ordering: false,
        info: false,
        initComplete: function() {
            
            // Select last selected device
            if (localStorage.getItem('sourceDevice') !== null) {
                devices_table.row(localStorage.getItem("sourceDevice")).select()
            } else {
                devices_table.row().select()
            }
            initStudiesTable()
            initDestinations()
        },            
    });

    // Enable select behaviour for device table
    $('#devices tbody').on('click', 'tr', function () {                
        if (!$(this).hasClass('selected')) {                  
            devices_table.rows().deselect()
            devices_table.row($(this)).select()
        }
    });

    // Show last query values in date and modalities selector
    if (localStorage.getItem('dateSelector') !== null ) {
        $("#startDate").val(localStorage.getItem("startDate"))
        $("#endDate").val(localStorage.getItem("endDate"))
        $("#" + localStorage.getItem("dateSelector")).prop("checked", true)
        if (localStorage.getItem("dateSelector") == "day") {
            $('#startDate').prop("disabled", false)
        }
        if (localStorage.getItem("dateSelector") == "between") {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", false)
        }
        JSON.parse(localStorage.modalities).forEach(function(item) {
            $("[name='modality'][value='"+item+"']").prop('checked',true)
        })

    } else {
        $("#today").prop("checked", true)
        document.getElementById('startDate').valueAsDate = new Date()
        document.getElementById('endDate').valueAsDate = new Date()
    }        

    // Enable/disable date pickers
    $("[name='date']").on('click', function(){

        if ($(this)[0].id == 'day') {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", true)
        }
        else if ($(this)[0].id == 'between') {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", false)
        }
        else {
            $('#startDate').prop("disabled", true)
            $('#endDate').prop("disabled", true)
        }
    })

    // Show search field placeholder
    $( "#search-field" ).change(function() {
        var value = $(this).val()
        if (value == "PatientName") {
            $("#search-value").attr("placeholder", "Nombre del paciente");
        }            
        else if (value == "PatientID") {
            $("#search-value").attr("placeholder", "HC/OPI");
        }
        else if (value == "StudyDescription") {
            $("#search-value").attr("placeholder", "Descripción del estudio");
        }

      });
});

// Initialize studies table
function initStudiesTable() {
    
    var devices_table = $('#devices').DataTable()
    var table_studies = $('#studies').DataTable({
        ajax: {
            url: "/empty_table",
            method: "POST",
            data: function() {
                    return JSON.stringify({
                        'dateSelector':$("[name='date']:checked").val(),
                        'startDate': $("#startDate").val(),
                        'endDate': $("#endDate").val(),
                        'device': devices_table.rows({ selected: true }).data()[0].name,
                        'modalities': $("[name='modality']:checked").map(function() {
                            return this.value
                        }).get(),
                        'searchField':$( "#search-field" ).val(),
                        'searchValue':$("#search-value").val()
                    })
                },
            contentType: 'application/json',
            dataType: "json"
          },              
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
            },
            { data: 'PatientName', title: 'Paciente' },
            { data: 'PatientID', title: 'ID' },
            { data: 'StudyDate', title: 'Fecha', type: 'date'},
            { data: 'StudyTime', title: 'Hora' },
            { data: 'ModalitiesInStudy', title: 'Modalidades' },
            { data: 'StudyDescription', title: 'Descripcion' },
            { data: 'ImgsStudy', title: 'Imgs' }
        ],
        order: [[3, 'asc'],[4, 'asc']],
        language: {
            search: 'Buscar',
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: " ",
            processing: " ",
        },
        processing: true,  
        paging: false,
        scrollY: '300px',
        filter: false,
        initComplete: function() {
            // Change ajax target
            table_studies.ajax.url('/search_studies')
            // Initialize table with data stored locally
            if (localStorage.getItem('studiesTable') !== null) {
                data = JSON.parse(localStorage.getItem('studiesTable'))
                table_studies.rows.add(data).draw()                
            }
        },
        select:         {
                            style: 'os',
                            selector: 'td',
                            info: false,
                        },
    });

    // Manage the study search (form submission)
    $("#search_studies").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();
        // Reload table
        table_studies.clear().draw()
        //Store the query data to be shown after refreshing the page
        sourceDevice = devices_table.rows({ selected: true })[0]
        dateSelector = $("[name='date']:checked").prop('id')
        startDate = $("#startDate").val()
        endDate = $("#endDate").val()
        modalities = $("[name='modality']:checked").map(function() {
            return this.value
        }).get(),
        
        table_studies.ajax.reload( function() {
            // Store the data locally to be shown after refreshing the page    
            localStorage.setItem("studiesTable",JSON.stringify(table_studies.rows().data().toArray()))
            localStorage.setItem("sourceDevice", sourceDevice)
            localStorage.setItem("dateSelector", dateSelector)
            localStorage.setItem("startDate", startDate)
            localStorage.setItem("endDate", endDate)
            localStorage.setItem("modalities", JSON.stringify(modalities))
        })
    });   
    
    // Add event listener for opening and closing details
    $('#studies tbody').on('click', 'td.dt-control', function () {
        var tr = $(this).closest('tr');
        var row = table_studies.row(tr);
 
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('shown');
        } else {
            // Open this row
            showStudy(row)            
            tr.addClass('shown');
        }
    });  

    // Add send button behaviour
    $("#sendForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();

        // Get destination device
        var ajax_data = {'destination': $("#destinations").val()}

        // Get selected rows
        var items = []
        var tr = $('.toSend')        
        for (var idx = 0; idx < tr.length; idx++){
            var element = tr[idx]
            items.push($(element.closest('table')).DataTable().row(element).data())                        
        }
        ajax_data.items = items
        $.ajax({
            url: "/move",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {
                
                // Show success message
                alert(response.message)
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            });

    });
}

function initDestinations() {
    // Append local device
    $('#destinations').append($('<option>', { 'Local' : 'Local' }).text('Local'));
    // Append remote devices
    var selectValues = $('#devices').DataTable().column(0).data()
    $.each(selectValues, function(key, value) {
        $('#destinations')
             .append($('<option>', { value : value })
             .text(value));
   });
}

// Show study details
function showStudy(row) {        
    
    row.child(`<table id="child_${row.data().StudyInstanceUID}" class="display compact" width="100%"> 
                
            </table>`).show();
    var childTable = $(jq("child_" + row.data().StudyInstanceUID)).DataTable({
        ajax: {
        url: "/get_study_data",
        method: "POST",
        data: function() { return JSON.stringify(row.data()) },
        contentType: 'application/json',
        dataType: "json"
      },
        columns: [
            
            { data: 'SeriesNumber', title: 'Numero' },
            { data: 'SeriesDate', title: 'Fecha' },
            { data: 'SeriesTime', title: 'Hora' },
            { data: 'SeriesDescription', title: 'Descripcion' },
            { data: 'Modality', title: 'Modalidad' },
            { data: 'ImgsSeries', title:'Imgs' },
            
        ],
        order: [[0, 'asc']],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: "<br><br>",
            processing: " ",
            loadingRecords: "<br>",
        },
        processing: true,
        paging: false,
        filter: false,
        info: false,
        select:         {
                            style: 'os',
                            selector: 'td',
                            info: false,
                        },
});
}

// Escape special characters in html element id (to be usable by jQuery)
function jq( myid ) {  
    return "#" + myid.replace( /(:|\.|\[|\]|,|=|@)/g, "\\$1" ); 
}

// Don't show alerts on ajax errors
$.fn.dataTable.ext.errMode = 'throw';