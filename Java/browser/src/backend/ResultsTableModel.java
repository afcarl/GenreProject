package backend;

import javax.swing.table.DefaultTableModel;

public class ResultsTableModel extends DefaultTableModel {

	static String[] COL_NAMES = {"HTID","Author","Title","Date"};
	public static int HTID_COL = 0;
	public static int AUTHOR_COL = 1;
	public static int TITLE_COL = 2;
	public static int DATE_COL = 3;
	
	public ResultsTableModel() {
		setColumnIdentifiers(COL_NAMES);
	}
	
	public void addResult(String htid, String author, String title, String date) {
		String[] row = new String[4];
		row[HTID_COL] = htid;
		row[AUTHOR_COL] = author;
		row[TITLE_COL] = title;
		row[DATE_COL] = date;
		addRow(row);
	}
	
}